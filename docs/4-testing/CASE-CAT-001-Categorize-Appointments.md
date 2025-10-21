# Test Case Template

## Test Case Information
- **Test Case ID**: TC-CAT-001
- **Test Case Name**: Appointment Categorization (AI-assisted and Manual Override)
- **Created By**: [Your Name]
- **Creation Date**: 2024-06-11
- **Last Updated**: 2024-06-11
- **Related Requirements**: FR-CAT-001, FR-CAT-002, FR-BIL-002, FR-BIL-005, NFR-USE-001
- **Priority**: High

## Test Objective
Verify that the system recommends billing categories for appointments using AI, allows user to override recommendations, and handles ambiguous/missing categories appropriately.

## Preconditions
- User is authenticated.
- Appointment exists.

## Test Data
- Appointment with subject, attendees, and location.
- Appointment with ambiguous/missing category.

## Test Steps
| Step # | Description | Expected Result     |
|--------|-------------|---------------------|
| 1      | System recommends category for appointment | Category is suggested using AI and rules |
| 2      | User overrides recommended category | User's selection is saved and used for billing |
| 3      | Appointment with ambiguous/missing category | System prompts user for input |

## Post-conditions
- Appointment has a correct billing category assigned.

## Special Requirements
- Use subject, attendees, and location for recommendation.

## Dependencies
- Categorization service, OpenAI API.

## Notes
- Test both AI and manual flows.

## Change Tracking

| Version | Date | Author | Description of Changes |
|---------|------|--------|------------------------|
| 1.0 | 2024-06-11 | [Your Name] | Initial version | 