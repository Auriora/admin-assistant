from typing import Any, List, Optional
from core.services.action_log_service import ActionLogService
from core.services.entity_association_service import EntityAssociationService
from core.services.prompt_service import PromptService
from core.services.chat_session_service import ChatSessionService

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
    ):
        self.action_log_service = action_log_service or ActionLogService()
        self.association_service = association_service or EntityAssociationService()
        self.prompt_service = prompt_service or PromptService()
        self.chat_session_service = chat_session_service or ChatSessionService()

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
        # 1. Fetch related appointments
        related = self.action_log_service.get_related_entities(action_log_id)
        from core.models.appointment import Appointment
        from core.repositories.appointment_repository_sqlalchemy import SQLAlchemyAppointmentRepository
        appointment_repo = SQLAlchemyAppointmentRepository(user=user, calendar_id=calendar_id)
        appointment_ids = [tid for ttype, tid in related if ttype == 'appointment']
        appointments = [appointment_repo.get_by_id(aid) for aid in appointment_ids]
        appointments = [a for a in appointments if a]

        # 2. Apply user resolution
        # a) Keep: do nothing
        keep_ids = set(resolution_data.get('keep', []))
        # b) Edit: update fields
        for edit in resolution_data.get('edit', []):
            appt = appointment_repo.get_by_id(edit['id'])
            if appt:
                for k, v in edit.get('fields', {}).items():
                    setattr(appt, k, v)
                appointment_repo.update(appt)
        # c) Merge: update one appointment, delete others
        merge = resolution_data.get('merge')
        if merge:
            into_id = merge.get('into')
            from_ids = merge.get('from', [])
            fields = merge.get('fields', {})
            appt = appointment_repo.get_by_id(into_id)
            if appt:
                for k, v in fields.items():
                    setattr(appt, k, v)
                appointment_repo.update(appt)
            for fid in from_ids:
                if fid != into_id:
                    appointment_repo.delete(fid)
        # d) Create: add new appointment
        create = resolution_data.get('create')
        if create:
            new_appt = Appointment(**create.get('fields', {}))
            appointment_repo.add(new_appt)
        # e) Delete: appointments not in keep/edit/merge/create
        handled_ids = keep_ids | {e['id'] for e in resolution_data.get('edit', [])} | set(merge.get('from', []) if merge else [])
        for appt in appointments:
            if getattr(appt, 'id') not in handled_ids:
                appointment_repo.delete(getattr(appt, 'id'))

        # 3. Mark the ActionLog as resolved
        self.action_log_service.transition_state(action_log_id, 'resolved')
        # 4. Optionally, log the resolution or update related entities

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