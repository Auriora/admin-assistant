"""
Unit tests for the overlap analysis CLI command
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timezone, timedelta
from typer.testing import CliRunner
from cli.main import app


class TestOverlapAnalysisCLI:
    """Test the calendar analyze-overlaps CLI command"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        # Set up in-memory database for tests
        os.environ['CORE_DATABASE_URL'] = 'sqlite:///:memory:'
    
    def _create_mock_appointment(self, subject, start_time, end_time, show_as="busy", importance="normal", categories=None):
        """Create a mock appointment for testing"""
        appointment = Mock()
        appointment.subject = subject
        appointment.start_time = start_time
        appointment.end_time = end_time
        appointment.show_as = show_as
        appointment.importance = importance
        appointment.categories = categories or []
        appointment.ms_event_id = f"test-{subject.replace(' ', '-').lower()}"
        return appointment
    
    @patch('cli.commands.calendar.resolve_cli_user')
    @patch('cli.commands.calendar.get_session')
    @patch('cli.common.utils.parse_flexible_date')
    def test_analyze_overlaps_no_appointments(self, mock_parse_flexible_date, mock_get_session, mock_resolve_user):
        """Test analyze-overlaps command when no appointments are found"""
        # Mock user resolution
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user

        # Mock date parsing
        from datetime import date
        mock_parse_flexible_date.side_effect = [date(2024, 1, 1), date(2024, 1, 2)]

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value = mock_session

        # Mock the entire query chain to return empty results
        # We need to mock the session.query().filter().all() chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = []
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query

        # Run the command
        result = self.runner.invoke(app, [
            'calendar', 'analyze-overlaps',
            '--user', '1',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-02'
        ])

        # Verify the command executed successfully
        assert result.exit_code == 0
        assert "No appointments found" in result.output
    
    @patch('cli.commands.calendar.resolve_cli_user')
    @patch('cli.commands.calendar.get_session')
    @patch('cli.common.utils.parse_flexible_date')
    @patch('core.utilities.calendar_recurrence_utility.expand_recurring_events_range')
    @patch('core.utilities.calendar_overlap_utility.detect_overlaps')
    def test_analyze_overlaps_no_overlaps_found(self, mock_detect_overlaps, mock_expand_recurring,
                                               mock_parse_flexible_date, mock_get_session, mock_resolve_user):
        """Test analyze-overlaps command when no overlaps are found"""
        # Mock user resolution
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user

        # Mock date parsing
        from datetime import date
        mock_parse_flexible_date.side_effect = [date(2024, 1, 1), date(2024, 1, 2)]

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value = mock_session

        # Create mock appointments
        now = datetime.now(timezone.utc)
        appointments = [
            self._create_mock_appointment("Meeting 1", now, now + timedelta(hours=1)),
            self._create_mock_appointment("Meeting 2", now + timedelta(hours=2), now + timedelta(hours=3))
        ]

        # Mock the query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = appointments
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        # Mock expansion and overlap detection
        mock_expand_recurring.return_value = appointments
        mock_detect_overlaps.return_value = []  # No overlaps
        
        # Run the command
        result = self.runner.invoke(app, [
            'calendar', 'analyze-overlaps', 
            '--user', '1',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-02'
        ])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        assert "No overlapping appointments found" in result.output
        assert "✓" in result.output
    
    @patch('cli.commands.calendar.resolve_cli_user')
    @patch('cli.commands.calendar.get_session')
    @patch('cli.common.utils.parse_flexible_date')
    @patch('core.utilities.calendar_recurrence_utility.expand_recurring_events_range')
    @patch('core.utilities.calendar_overlap_utility.detect_overlaps')
    def test_analyze_overlaps_with_overlaps_no_auto_resolve(self, mock_detect_overlaps, mock_expand_recurring,
                                                           mock_parse_flexible_date, mock_get_session, mock_resolve_user):
        """Test analyze-overlaps command when overlaps are found but auto-resolve is not enabled"""
        # Mock user resolution
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user

        # Mock date parsing
        from datetime import date
        mock_parse_flexible_date.side_effect = [date(2024, 1, 1), date(2024, 1, 2)]

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value = mock_session

        # Create overlapping mock appointments
        now = datetime.now(timezone.utc)
        appointment1 = self._create_mock_appointment("Meeting 1", now, now + timedelta(hours=2))
        appointment2 = self._create_mock_appointment("Meeting 2", now + timedelta(minutes=30), now + timedelta(hours=1, minutes=30))

        appointments = [appointment1, appointment2]

        # Mock the query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = appointments
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        # Mock expansion and overlap detection
        mock_expand_recurring.return_value = appointments
        mock_detect_overlaps.return_value = [[appointment1, appointment2]]  # One overlap group
        
        # Run the command
        result = self.runner.invoke(app, [
            'calendar', 'analyze-overlaps', 
            '--user', '1',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-02'
        ])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        assert "Found 1 overlap groups" in result.output
        assert "Use --auto-resolve to apply automatic resolution rules" in result.output
        assert "Meeting 1" in result.output
        assert "Meeting 2" in result.output
    
    @patch('cli.commands.calendar.resolve_cli_user')
    @patch('cli.commands.calendar.get_session')
    @patch('cli.common.utils.parse_flexible_date')
    @patch('core.utilities.calendar_recurrence_utility.expand_recurring_events_range')
    @patch('core.utilities.calendar_overlap_utility.detect_overlaps')
    @patch('core.services.enhanced_overlap_resolution_service.EnhancedOverlapResolutionService')
    def test_analyze_overlaps_with_auto_resolve(self, mock_overlap_service_class, mock_detect_overlaps,
                                               mock_expand_recurring, mock_parse_flexible_date, mock_get_session, mock_resolve_user):
        """Test analyze-overlaps command with auto-resolve enabled"""
        # Mock user resolution
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user

        # Mock date parsing
        from datetime import date
        mock_parse_flexible_date.side_effect = [date(2024, 1, 1), date(2024, 1, 2)]

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value = mock_session

        # Create overlapping mock appointments
        now = datetime.now(timezone.utc)
        appointment1 = self._create_mock_appointment("Meeting 1", now, now + timedelta(hours=2), show_as="busy", importance="high")
        appointment2 = self._create_mock_appointment("Meeting 2", now + timedelta(minutes=30), now + timedelta(hours=1, minutes=30), show_as="tentative", importance="normal")

        appointments = [appointment1, appointment2]

        # Mock the query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = appointments
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query
        
        # Mock expansion and overlap detection
        mock_expand_recurring.return_value = appointments
        mock_detect_overlaps.return_value = [[appointment1, appointment2]]  # One overlap group
        
        # Mock overlap resolution service
        mock_overlap_service = Mock()
        mock_overlap_service_class.return_value = mock_overlap_service
        mock_overlap_service.apply_automatic_resolution_rules.return_value = {
            'resolved': [appointment1],  # High importance appointment wins
            'conflicts': [],  # No remaining conflicts
            'filtered': [appointment2],  # Tentative appointment filtered out
            'resolution_log': ['Resolved conflict: High importance appointment kept, tentative discarded']
        }
        
        # Run the command with auto-resolve
        result = self.runner.invoke(app, [
            'calendar', 'analyze-overlaps', 
            '--user', '1',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-02',
            '--auto-resolve'
        ])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        assert "Found 1 overlap groups" in result.output
        assert "All overlaps resolved automatically" in result.output
        assert "✓" in result.output
        assert "Auto-Resolved" in result.output
        assert "Remaining Conflicts" in result.output
    
    @patch('cli.commands.calendar.resolve_cli_user')
    @patch('cli.commands.calendar.get_session')
    @patch('cli.common.utils.parse_flexible_date')
    def test_analyze_overlaps_missing_user(self, mock_parse_flexible_date, mock_get_session, mock_resolve_user):
        """Test analyze-overlaps command with missing user parameter"""
        # Mock user resolution to succeed with default user
        mock_user = Mock(id=1, email='test@example.com')
        mock_resolve_user.return_value = mock_user

        # Mock date parsing
        from datetime import date
        mock_parse_flexible_date.side_effect = [date(2024, 1, 1), date(2024, 1, 2)]

        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value = mock_session

        # Mock the query chain to return empty results
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = []
        mock_query.filter.return_value = mock_filter
        mock_session.query.return_value = mock_query

        result = self.runner.invoke(app, [
            'calendar', 'analyze-overlaps',
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-02'
        ])

        # Should succeed since user resolution falls back to defaults
        assert result.exit_code == 0
        assert "No appointments found" in result.output
    
    @patch('cli.commands.calendar.resolve_cli_user')
    def test_analyze_overlaps_user_not_found(self, mock_resolve_user):
        """Test analyze-overlaps command when user is not found"""
        # Mock user resolution to fail
        mock_resolve_user.side_effect = ValueError("No user found for identifier: 999")

        # Run the command
        result = self.runner.invoke(app, [
            'calendar', 'analyze-overlaps',
            '--user', '999',  # Non-existent user
            '--start-date', '2024-01-01',
            '--end-date', '2024-01-02'
        ])

        # Should fail due to user not found
        assert result.exit_code == 1
        assert "No user found for identifier: 999" in result.output
