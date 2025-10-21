# Test Case Template

## Test Case Information
- **Test Case ID**: TC-PRI-001
- **Test Case Name**: Privacy Management for Appointments
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-PRI-001, FR-PRI-002, FR-PRI-003, NFR-SEC-001
- **Priority**: High

## Test Objective
Verify that the system automatically marks personal and travel appointments as private, excludes private appointments from timesheet exports, and maintains a log of privacy changes with rollback capability.

## Preconditions
- User is authenticated.
- Appointment exists.

## Test Data
- Personal appointment.
- Travel appointment.

## Test Steps
| Step # | Description | Expected Result     |
|--------|-------------|---------------------|
| 1      | System identifies personal/travel appointment | Appointment is marked as private |
| 2      | Generate timesheet export | Private appointments are excluded |
| 3      | User reviews privacy log | All privacy changes are logged |
| 4      | User rolls back a privacy change | Appointment privacy status is reverted |

## Post-conditions
- Private appointments are excluded from exports.
- Privacy changes are logged and reversible.

## Special Requirements
- Privacy log with rollback via UI.

## Dependencies
- Privacy/categorization service, export service.

## Notes
- Test both automatic and manual privacy management.

## Change Tracking

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2024-06-11 | [Your Name] | Initial version | 