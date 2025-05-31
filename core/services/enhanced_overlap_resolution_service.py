from typing import List, Tuple, Dict, Any, Optional
from core.models.appointment import Appointment
import logging

logger = logging.getLogger(__name__)


class EnhancedOverlapResolutionService:
    """Enhanced overlap resolution with automatic rules."""
    
    def apply_automatic_resolution_rules(self, overlapping_appointments: List[Appointment]) -> Dict[str, Any]:
        """
        Apply automatic resolution rules in order:
        1. Filter out 'Free' appointments
        2. Discard 'Tentative' in favor of confirmed
        3. Use Priority (importance) for final resolution
        
        Args:
            overlapping_appointments: List of overlapping appointments to resolve
            
        Returns:
            Dict with keys:
            - 'resolved': List of appointments to keep after resolution
            - 'conflicts': List of appointments that still conflict (need manual resolution)
            - 'filtered': List of appointments that were filtered out
            - 'resolution_log': List of resolution steps taken
        """
        if not overlapping_appointments:
            return {
                'resolved': [],
                'conflicts': [],
                'filtered': [],
                'resolution_log': []
            }
        
        resolution_log = []
        filtered_appointments = []
        
        # Step 1: Filter out 'Free' appointments
        remaining_appointments, free_appointments = self.filter_free_appointments(overlapping_appointments)
        if free_appointments:
            filtered_appointments.extend(free_appointments)
            resolution_log.append(f"Filtered out {len(free_appointments)} 'Free' appointments")
        
        # If only one appointment remains after filtering, it's resolved
        if len(remaining_appointments) <= 1:
            return {
                'resolved': remaining_appointments,
                'conflicts': [],
                'filtered': filtered_appointments,
                'resolution_log': resolution_log
            }
        
        # Step 2: Resolve Tentative vs Confirmed conflicts
        remaining_appointments, tentative_appointments = self.resolve_tentative_conflicts(remaining_appointments)
        if tentative_appointments:
            filtered_appointments.extend(tentative_appointments)
            resolution_log.append(f"Discarded {len(tentative_appointments)} 'Tentative' appointments in favor of confirmed")
        
        # If only one appointment remains after tentative resolution, it's resolved
        if len(remaining_appointments) <= 1:
            return {
                'resolved': remaining_appointments,
                'conflicts': [],
                'filtered': filtered_appointments,
                'resolution_log': resolution_log
            }
        
        # Step 3: Resolve by priority/importance
        try:
            primary_appointment, secondary_appointments = self.resolve_by_priority(remaining_appointments)
            if secondary_appointments:
                filtered_appointments.extend(secondary_appointments)
                resolution_log.append(f"Selected highest priority appointment, filtered {len(secondary_appointments)} lower priority")
            
            return {
                'resolved': [primary_appointment],
                'conflicts': [],
                'filtered': filtered_appointments,
                'resolution_log': resolution_log
            }
        except ValueError as e:
            # Unable to resolve by priority - return as conflicts for manual resolution
            resolution_log.append(f"Unable to resolve by priority: {str(e)}")
            return {
                'resolved': [],
                'conflicts': remaining_appointments,
                'filtered': filtered_appointments,
                'resolution_log': resolution_log
            }
    
    def filter_free_appointments(self, appointments: List[Appointment]) -> Tuple[List[Appointment], List[Appointment]]:
        """
        Separate Free appointments from others.
        
        Returns:
            Tuple of (non_free_appointments, free_appointments)
        """
        non_free = []
        free = []
        
        for appt in appointments:
            show_as = getattr(appt, 'show_as', None)
            if show_as and str(show_as).lower() == 'free':
                free.append(appt)
            else:
                non_free.append(appt)
        
        return non_free, free
    
    def resolve_tentative_conflicts(self, appointments: List[Appointment]) -> Tuple[List[Appointment], List[Appointment]]:
        """
        Resolve Tentative vs Confirmed conflicts.
        If there are both tentative and confirmed appointments, keep only confirmed ones.
        
        Returns:
            Tuple of (confirmed_or_all_appointments, discarded_tentative_appointments)
        """
        confirmed = []
        tentative = []
        
        for appt in appointments:
            show_as = getattr(appt, 'show_as', None)
            if show_as and str(show_as).lower() == 'tentative':
                tentative.append(appt)
            else:
                # Treat anything that's not explicitly tentative as confirmed
                confirmed.append(appt)
        
        # If we have both confirmed and tentative, discard tentative
        if confirmed and tentative:
            return confirmed, tentative
        
        # If all are tentative or all are confirmed, keep all
        return appointments, []
    
    def resolve_by_priority(self, appointments: List[Appointment]) -> Tuple[Appointment, List[Appointment]]:
        """
        Resolve remaining conflicts using importance/priority.
        
        Returns:
            Tuple of (primary_appointment, secondary_appointments)
            
        Raises:
            ValueError: If unable to determine priority (e.g., all have same priority)
        """
        if not appointments:
            raise ValueError("No appointments to resolve")
        
        if len(appointments) == 1:
            return appointments[0], []
        
        # Calculate priority scores for all appointments
        scored_appointments = []
        for appt in appointments:
            score = self.get_appointment_priority_score(appt)
            scored_appointments.append((score, appt))
        
        # Sort by priority score (highest first)
        scored_appointments.sort(key=lambda x: x[0], reverse=True)
        
        # Check if we have a clear winner
        highest_score = scored_appointments[0][0]
        highest_priority_appointments = [appt for score, appt in scored_appointments if score == highest_score]
        
        if len(highest_priority_appointments) == 1:
            # Clear winner
            primary = highest_priority_appointments[0]
            secondary = [appt for score, appt in scored_appointments if score < highest_score]
            return primary, secondary
        else:
            # Multiple appointments with same highest priority - cannot auto-resolve
            raise ValueError(f"Multiple appointments have the same highest priority ({highest_score})")
    
    def get_appointment_priority_score(self, appointment: Appointment) -> int:
        """
        Calculate priority score for appointment.
        
        Returns:
            int: Priority score (High=3, Normal=2, Low=1, Unknown=2)
        """
        importance = getattr(appointment, 'importance', None)
        
        if not importance:
            return 2  # Default to normal priority
        
        importance_str = str(importance).lower()
        
        if importance_str == 'high':
            return 3
        elif importance_str == 'normal':
            return 2
        elif importance_str == 'low':
            return 1
        else:
            # Unknown importance, treat as normal
            return 2
