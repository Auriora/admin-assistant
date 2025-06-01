# AI Implementation Prompts

## Document Information
- **Document ID**: AIP-001
- **Document Name**: AI Implementation Prompts
- **Created By**: Admin Assistant System
- **Creation Date**: 2024-12-19
- **Purpose**: Ready-to-use prompts for AI-assisted development

## Overview

This document contains specific, detailed prompts for implementing the remaining Admin Assistant features using AI assistance. Each prompt follows the Solo-Developer-AI-Process framework and includes complete context about the existing codebase.

## Prompt 1: PDF Timesheet Generation Service

### Context
The Admin Assistant project has a complete calendar archiving system with CategoryProcessingService that parses customer and billing information from Outlook categories. We need to implement PDF timesheet generation from archived appointments.

### Prompt
```
Create a comprehensive TimesheetGenerationService for the admin-assistant project that generates PDF timesheets from archived calendar appointments.

EXISTING CODEBASE CONTEXT:
- CategoryProcessingService already parses categories in format "<customer name> - <billing type>"
- Appointment model has all required fields (start_time, end_time, subject, categories, show_as, sensitivity)
- AuditLogService exists for operation logging
- Repository pattern is used throughout (see core/repositories/)
- Service pattern is used throughout (see core/services/)

REQUIREMENTS:
1. Extract archived appointments from database for specified date range
2. Use CategoryProcessingService to parse customer and billing information
3. Calculate total hours per customer/billing type combination
4. Generate PDF timesheet matching professional format
5. Exclude private appointments (sensitivity != 'Normal') and 'Free' status appointments
6. Include summary statistics and validation
7. Support both individual customer timesheets and combined reports

TECHNICAL SPECIFICATIONS:
- File: core/services/timesheet_generation_service.py
- Use ReportLab for PDF generation
- Integrate with existing SQLAlchemy models
- Follow existing error handling patterns
- Include comprehensive logging
- Return structured results with file paths and statistics

METHODS TO IMPLEMENT:
- generate_timesheet(user_id, start_date, end_date, customer_filter=None) -> Dict
- calculate_category_hours(appointments) -> Dict
- format_pdf_content(timesheet_data) -> bytes
- validate_timesheet_data(appointments) -> List[str]
- get_timesheet_statistics(timesheet_data) -> Dict

INTEGRATION POINTS:
- Use existing CategoryProcessingService for category parsing
- Use AuditLogService for operation logging
- Follow existing repository pattern for data access
- Integrate with CLI interface (add timesheet generate command)

Include comprehensive unit tests with realistic test data and edge cases.
```

## Prompt 2: Travel Detection Service

### Context
The Admin Assistant project processes calendar appointments and needs to detect missing travel appointments between different locations to ensure accurate time tracking.

### Prompt
```
Create a TravelDetectionService for the admin-assistant project that analyzes appointment sequences to detect missing travel time and suggest travel appointments.

EXISTING CODEBASE CONTEXT:
- Appointment model includes location field
- CategoryProcessingService handles special categories like "Online"
- Location model exists for location management
- MS Graph integration for calendar operations
- Existing audit logging and error handling patterns

REQUIREMENTS:
1. Analyze sequences of appointments to detect location changes
2. Calculate travel time between locations using Google Directions API
3. Identify missing travel appointments in schedule gaps
4. Handle special cases:
   - "Online" appointments require no travel
   - Home/Office locations are base locations
   - Travel to external locations should trigger OOO status
5. Suggest travel appointments with realistic travel times
6. Integrate with existing privacy automation

TECHNICAL SPECIFICATIONS:
- File: core/services/travel_detection_service.py
- Integrate Google Directions API with proper error handling
- Use existing Location model for location management
- Follow existing service patterns and error handling
- Include rate limiting and quota management for Google API
- Support both analysis mode and suggestion mode

METHODS TO IMPLEMENT:
- analyze_travel_gaps(appointments, user_locations) -> List[Dict]
- calculate_travel_time(origin, destination) -> Dict
- suggest_travel_appointments(travel_gaps) -> List[Appointment]
- is_travel_required(from_location, to_location) -> bool
- should_mark_ooo(location) -> bool
- validate_appointment_sequence(appointments) -> List[str]

GOOGLE DIRECTIONS INTEGRATION:
- Use Google Directions API for travel time calculation
- Include traffic data when available
- Handle API errors gracefully with fallback estimates
- Implement proper rate limiting
- Cache common routes to reduce API calls

INTEGRATION POINTS:
- Use CategoryProcessingService to identify "Online" appointments
- Integrate with existing privacy automation for OOO marking
- Use AuditLogService for operation logging
- Add CLI command: admin-assistant calendar analyze-travel

Include comprehensive unit tests with mocked Google API responses and realistic travel scenarios.
```

## Prompt 3: Xero Integration Service

### Context
The Admin Assistant project generates timesheets and needs to integrate with Xero accounting software to create invoices with timesheet attachments.

### Prompt
```
Create a XeroIntegrationService for the admin-assistant project that integrates with Xero API to generate invoices from timesheet data.

EXISTING CODEBASE CONTEXT:
- TimesheetGenerationService generates PDF timesheets (to be implemented first)
- CategoryProcessingService parses customer and billing information
- User model contains customer and billing configuration
- Existing audit logging and error handling patterns
- Repository pattern used throughout

REQUIREMENTS:
1. Integrate with Xero API for invoice creation and management
2. Map timesheet data to Xero invoice format with line items
3. Attach PDF timesheets to invoices in Xero
4. Track invoice status and payment information
5. Handle API errors, retries, and rate limiting
6. Support both individual customer invoices and batch processing
7. Maintain audit trail of all Xero operations

TECHNICAL SPECIFICATIONS:
- File: core/services/xero_integration_service.py
- Use official Xero Python SDK
- Implement OAuth2 authentication for Xero
- Follow existing error handling and retry patterns
- Include comprehensive logging and audit trail
- Support sandbox and production environments

METHODS TO IMPLEMENT:
- create_invoice(timesheet_data, customer_info) -> Dict
- attach_timesheet_pdf(invoice_id, pdf_data) -> bool
- get_invoice_status(invoice_id) -> Dict
- map_timesheet_to_invoice(timesheet_data) -> Dict
- handle_xero_webhook(webhook_data) -> None
- sync_customer_data() -> Dict
- validate_xero_configuration() -> List[str]

XERO API INTEGRATION:
- Use Xero Python SDK for API operations
- Implement proper OAuth2 flow for authentication
- Handle rate limiting (60 calls per minute)
- Implement retry logic for transient failures
- Support both sandbox and production tenants

INVOICE MAPPING:
- Map customer names to Xero contacts
- Convert timesheet line items to invoice line items
- Apply appropriate tax rates and billing rates
- Include timesheet period in invoice description
- Attach PDF timesheet as supporting document

INTEGRATION POINTS:
- Use TimesheetGenerationService for PDF creation
- Use CategoryProcessingService for customer/billing parsing
- Use AuditLogService for comprehensive operation logging
- Add CLI commands: admin-assistant xero create-invoice, admin-assistant xero sync-status

Include comprehensive unit tests with mocked Xero API responses and realistic invoice scenarios.
```

## Prompt 4: Enhanced Web Interface

### Context
The Admin Assistant project has a basic web interface with MS365 authentication but needs feature-specific pages for timesheet generation, travel management, and system configuration.

### Prompt
```
Create enhanced web interface pages for the admin-assistant project to provide user-friendly access to timesheet generation, travel management, and system configuration.

EXISTING CODEBASE CONTEXT:
- Flask web application with MS365 OAuth authentication
- Bootstrap-based UI framework
- Existing services: TimesheetGenerationService, TravelDetectionService, XeroIntegrationService
- CLI interface exists for all operations
- Audit logging system for all operations

REQUIREMENTS:
1. Timesheet generation page with date range selection and customer filtering
2. Travel analysis page showing detected gaps and suggestions
3. System configuration page for Xero, Google API, and other settings
4. Dashboard showing recent operations and system status
5. Audit log viewer with filtering and search capabilities
6. Responsive design for mobile and desktop
7. Real-time status updates for long-running operations

TECHNICAL SPECIFICATIONS:
- Use existing Flask application structure
- Extend existing Bootstrap templates
- Implement AJAX for dynamic updates
- Follow existing authentication patterns
- Include proper error handling and user feedback
- Support file downloads for PDFs and reports

PAGES TO IMPLEMENT:

1. TIMESHEET GENERATION PAGE (/timesheets)
   - Date range picker with presets (last week, last month, custom)
   - Customer filter dropdown
   - Generate button with progress indicator
   - Download links for generated PDFs
   - Preview of timesheet data before generation

2. TRAVEL ANALYSIS PAGE (/travel)
   - Date range selection for analysis
   - Interactive calendar view showing appointments and travel gaps
   - Travel suggestions with Google Maps integration
   - Approve/reject travel appointment suggestions
   - Travel statistics and insights

3. CONFIGURATION PAGE (/config)
   - Xero API configuration and connection status
   - Google Directions API settings
   - Archive configuration management
   - User preferences and default settings
   - Test connection buttons for external APIs

4. DASHBOARD PAGE (/)
   - Recent operations summary
   - System health indicators
   - Quick action buttons
   - Upcoming scheduled jobs
   - Error notifications and alerts

5. AUDIT LOG PAGE (/audit)
   - Searchable audit log with filters
   - Operation details and drill-down
   - Export functionality
   - Performance metrics visualization

INTEGRATION POINTS:
- Use all existing services through proper service layer
- Implement WebSocket or Server-Sent Events for real-time updates
- Use existing audit logging for all user actions
- Follow existing error handling patterns
- Integrate with CLI commands for backend operations

Include proper form validation, CSRF protection, and accessibility features.
```

## Prompt 5: Email Service Integration

### Context
The Admin Assistant project needs to send timesheet reports to clients and system notifications to users via email.

### Prompt
```
Create an EmailService for the admin-assistant project that handles client timesheet delivery and system notifications.

EXISTING CODEBASE CONTEXT:
- TimesheetGenerationService generates PDF timesheets
- User model contains email configuration
- Existing audit logging and error handling patterns
- Background job system for scheduled operations

REQUIREMENTS:
1. Send timesheet PDFs to clients via email
2. Support scheduled weekly/monthly timesheet delivery
3. Send system notifications for errors and important events
4. Track email delivery status and bounces
5. Support email templates for different message types
6. Handle email provider failures with retry logic
7. Maintain audit trail of all email operations

TECHNICAL SPECIFICATIONS:
- File: core/services/email_service.py
- Support multiple email providers (SMTP, SendGrid, AWS SES)
- Use Jinja2 templates for email content
- Implement proper error handling and retry logic
- Include delivery tracking and bounce handling
- Support both HTML and plain text emails

METHODS TO IMPLEMENT:
- send_timesheet_email(recipient, timesheet_pdf, period_info) -> Dict
- send_notification_email(recipient, notification_type, details) -> Dict
- schedule_recurring_emails(user_id, schedule_config) -> bool
- track_delivery_status(email_id) -> Dict
- handle_bounce_notification(bounce_data) -> None
- validate_email_configuration() -> List[str]
- get_email_statistics(date_range) -> Dict

EMAIL TEMPLATES:
- Timesheet delivery template with professional formatting
- System notification templates for different alert types
- Error notification templates with technical details
- Welcome and configuration emails for new users

INTEGRATION POINTS:
- Use TimesheetGenerationService for PDF attachment
- Use background job system for scheduled delivery
- Use AuditLogService for comprehensive email logging
- Add CLI commands: admin-assistant email send-timesheet, admin-assistant email test-config

DELIVERY TRACKING:
- Track email send status (sent, delivered, bounced, failed)
- Handle webhook notifications from email providers
- Implement retry logic for failed deliveries
- Log all email events for audit and troubleshooting

Include comprehensive unit tests with mocked email provider responses and realistic email scenarios.
```

## Usage Instructions

### For Each Prompt:

1. **Copy the complete prompt** including context and requirements
2. **Paste into your AI assistant** (Claude, ChatGPT, etc.)
3. **Review the generated code** for completeness and integration points
4. **Run the suggested tests** to validate functionality
5. **Integrate with existing codebase** following the specified patterns

### Implementation Order:

1. **Start with Prompt 1** (PDF Timesheet Generation) - Core business functionality
2. **Continue with Prompt 2** (Travel Detection) - Workflow enhancement
3. **Implement Prompt 3** (Xero Integration) - External integration
4. **Add Prompt 4** (Web Interface) - User experience
5. **Finish with Prompt 5** (Email Service) - Communication features

### Testing Strategy:

- Each prompt includes unit test requirements
- Test with real data from your Outlook calendar
- Validate integration points with existing services
- Perform end-to-end testing of complete workflows

---

*These prompts are designed to work with the existing Admin Assistant codebase and follow established patterns for consistency and maintainability.*
