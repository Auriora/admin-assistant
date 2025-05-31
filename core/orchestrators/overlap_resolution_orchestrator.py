from typing import Any, List, Optional
import time
from core.services.action_log_service import ActionLogService
from core.services.entity_association_service import EntityAssociationService
from core.services.prompt_service import PromptService
from core.services.chat_session_service import ChatSessionService
from core.services.audit_log_service import AuditLogService
from core.utilities.audit_logging_utility import AuditContext, AuditLogHelper

class OverlapResolutionOrchestrator:
    """
    Orchestrator for managing manual overlap resolution, chat/AI suggestions, and action/task management.
    Integrates ActionLogService, EntityAssociationService, PromptService, and ChatSessionService.
    """
    def __init__(
        self,
        action_log_service: Optional[ActionLogService] = None,
        association_service: Optional[EntityAssociationService] = None,
        prompt_service: Optional[PromptService] = None,
        chat_session_service: Optional[ChatSessionService] = None,
        audit_log_service: Optional[AuditLogService] = None,
    ):
        self.action_log_service = action_log_service or ActionLogService()
        self.association_service = association_service or EntityAssociationService()
        self.prompt_service = prompt_service or PromptService()
        self.chat_session_service = chat_session_service or ChatSessionService()
        self.audit_log_service = audit_log_service or AuditLogService()

    def get_open_tasks(self, user_id: int) -> List[Any]:
        """
        Fetch all open ActionLog tasks for the user, with related entities.
        """
        tasks = self.action_log_service.list_by_state('open')
        return [
            {
                "task": t,
                "related": self.action_log_service.get_related_entities(getattr(t, 'id'))
            }
            for t in tasks if getattr(t, 'user_id', None) == user_id
        ]

    def resolve_overlap(self, action_log_id: int, resolution_data: dict, user: Any, calendar_id: Any) -> None:
        """
        Apply a user-driven resolution to an overlap task:
        - Fetch related appointments via EntityAssociationService.
        - Apply user resolution: keep, edit, merge, or create appointments as specified in resolution_data.
        - Update or delete appointments as needed.
        - Mark the ActionLog as resolved and log the action.
        :param action_log_id: The ActionLog/task ID.
        :param resolution_data: Dict specifying the resolution.
        :param user: The user object (required for repository).
        :param calendar_id: The calendar ID (required for repository).
        """
        # Generate correlation ID for this resolution operation
        correlation_id = self.audit_log_service.generate_correlation_id()

        # Create audit context for the overlap resolution
        with AuditContext(
            audit_service=self.audit_log_service,
            user_id=user.id,
            action_type='overlap_resolution',
            operation='resolve_overlap',
            resource_type='action_log',
            resource_id=str(action_log_id),
            correlation_id=correlation_id
        ) as audit_ctx:

            # Add operation parameters to audit log
            audit_ctx.set_request_data({
                'action_log_id': action_log_id,
                'resolution_data': resolution_data,
                'calendar_id': str(calendar_id)
            })

            # 1. Fetch related appointments
            audit_ctx.add_detail('phase', 'fetching_appointments')
            related = self.action_log_service.get_related_entities(action_log_id)
            from core.models.appointment import Appointment
            from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
            appointment_repo = SQLAlchemyAppointmentRepository(user=user, calendar_id=calendar_id)
            appointment_ids = [tid for ttype, tid in related if ttype == 'appointment']
            appointments = [appointment_repo.get_by_id(aid) for aid in appointment_ids]
            appointments = [a for a in appointments if a]

            audit_ctx.add_detail('related_appointments_count', len(appointments))
            audit_ctx.add_detail('appointment_ids', appointment_ids)

            # 2. Apply user resolution
            audit_ctx.add_detail('phase', 'applying_resolution')
            resolution_actions = []

            # a) Keep: do nothing
            keep_ids = set(resolution_data.get('keep', []))
            if keep_ids:
                resolution_actions.append(f"Kept {len(keep_ids)} appointments")
                audit_ctx.add_detail('kept_appointments', list(keep_ids))

            # b) Edit: update fields
            edited_count = 0
            for edit in resolution_data.get('edit', []):
                appt = appointment_repo.get_by_id(edit['id'])
                if appt:
                    old_values = {k: getattr(appt, k, None) for k in edit.get('fields', {}).keys()}
                    for k, v in edit.get('fields', {}).items():
                        setattr(appt, k, v)
                    appointment_repo.update(appt)
                    edited_count += 1

                    # Log the specific changes made
                    AuditLogHelper.log_data_modification(
                        user_id=user.id,
                        operation='edit_appointment_in_resolution',
                        resource_type='appointment',
                        resource_id=str(edit['id']),
                        old_values=old_values,
                        new_values=edit.get('fields', {}),
                        correlation_id=correlation_id
                    )

            if edited_count > 0:
                resolution_actions.append(f"Edited {edited_count} appointments")
                audit_ctx.add_detail('edited_appointments_count', edited_count)

            # c) Merge: update one appointment, delete others
            merge = resolution_data.get('merge')
            if merge:
                into_id = merge.get('into')
                from_ids = merge.get('from', [])
                fields = merge.get('fields', {})
                appt = appointment_repo.get_by_id(into_id)
                if appt:
                    old_values = {k: getattr(appt, k, None) for k in fields.keys()}
                    for k, v in fields.items():
                        setattr(appt, k, v)
                    appointment_repo.update(appt)

                    # Log the merge operation
                    AuditLogHelper.log_data_modification(
                        user_id=user.id,
                        operation='merge_appointment_in_resolution',
                        resource_type='appointment',
                        resource_id=str(into_id),
                        old_values=old_values,
                        new_values=fields,
                        correlation_id=correlation_id
                    )

                deleted_count = 0
                for fid in from_ids:
                    if fid != into_id:
                        appointment_repo.delete(fid)
                        deleted_count += 1

                        # Log deletion
                        self.audit_log_service.log_operation(
                            user_id=user.id,
                            action_type='overlap_resolution',
                            operation='delete_merged_appointment',
                            status='success',
                            message=f"Deleted appointment {fid} as part of merge operation",
                            resource_type='appointment',
                            resource_id=str(fid),
                            correlation_id=correlation_id
                        )

                resolution_actions.append(f"Merged {len(from_ids)} appointments into 1, deleted {deleted_count}")
                audit_ctx.add_detail('merge_operation', {
                    'into_id': into_id,
                    'from_ids': from_ids,
                    'deleted_count': deleted_count
                })

            # d) Create: add new appointment
            create = resolution_data.get('create')
            created_count = 0
            if create:
                new_appt = Appointment(**create.get('fields', {}))
                appointment_repo.add(new_appt)
                created_count = 1
                resolution_actions.append(f"Created {created_count} new appointment")
                audit_ctx.add_detail('created_appointments_count', created_count)

                # Log creation
                self.audit_log_service.log_operation(
                    user_id=user.id,
                    action_type='overlap_resolution',
                    operation='create_appointment_in_resolution',
                    status='success',
                    message=f"Created new appointment as part of resolution",
                    resource_type='appointment',
                    resource_id=str(getattr(new_appt, 'id', 'new')),
                    details={'fields': create.get('fields', {})},
                    correlation_id=correlation_id
                )

            # e) Delete: appointments not in keep/edit/merge/create
            handled_ids = keep_ids | {e['id'] for e in resolution_data.get('edit', [])} | set(merge.get('from', []) if merge else [])
            deleted_unhandled_count = 0
            for appt in appointments:
                if getattr(appt, 'id') not in handled_ids:
                    appointment_repo.delete(getattr(appt, 'id'))
                    deleted_unhandled_count += 1

                    # Log deletion
                    self.audit_log_service.log_operation(
                        user_id=user.id,
                        action_type='overlap_resolution',
                        operation='delete_unhandled_appointment',
                        status='success',
                        message=f"Deleted unhandled appointment {getattr(appt, 'id')}",
                        resource_type='appointment',
                        resource_id=str(getattr(appt, 'id')),
                        correlation_id=correlation_id
                    )

            if deleted_unhandled_count > 0:
                resolution_actions.append(f"Deleted {deleted_unhandled_count} unhandled appointments")
                audit_ctx.add_detail('deleted_unhandled_count', deleted_unhandled_count)

            # 3. Mark the ActionLog as resolved
            audit_ctx.add_detail('phase', 'finalizing')
            self.action_log_service.transition_state(action_log_id, 'resolved')

            # Set final audit details
            audit_ctx.add_detail('resolution_actions', resolution_actions)
            audit_ctx.add_detail('total_appointments_affected', len(appointments))
            audit_ctx.set_response_data({
                'action_log_id': action_log_id,
                'resolution_actions': resolution_actions,
                'correlation_id': correlation_id
            })

    def get_ai_suggestions(self, action_log_id: int, user_id: int) -> Optional[str]:
        """
        Fetch AI suggestions for a given action/task using PromptService and ChatSessionService.
        """
        # TODO: Integrate with OpenAI or other AI provider
        prompt = self.prompt_service.get_most_relevant_prompt(user_id, 'overlap_resolution')
        # Optionally, use chat history for context
        chat_sessions = self.chat_session_service.list_by_action(action_log_id)
        # Placeholder: return prompt content
        return getattr(prompt, 'content', None) if prompt else None

    def start_or_continue_chat(self, action_log_id: int, user_id: int, message: str) -> Any:
        """
        Start or continue a chat session for a given action/task.
        """
        chat_sessions = self.chat_session_service.list_by_action(action_log_id)
        if chat_sessions:
            session = chat_sessions[0]
        else:
            # Create new chat session and associate
            from core.models.chat_session import ChatSession
            session = ChatSession(user_id=user_id, messages=[{"sender": "user", "content": message}])
            self.chat_session_service.create(session)
            self.association_service.associate(
                source_type='chat_session',
                source_id=getattr(session, 'id'),
                target_type='action_log',
                target_id=action_log_id,
                association_type='overlap_resolution_chat'
            )
        self.chat_session_service.append_message(getattr(session, 'id'), {"sender": "user", "content": message})
        return self.chat_session_service.get_chat_history(getattr(session, 'id')) 