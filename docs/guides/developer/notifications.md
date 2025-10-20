# Notification Guidelines for Admin Assistant

## Purpose
Notifications inform users of important events, errors, progress, or required actions. They must be timely, actionable, and non-intrusive.

## When to Use Notifications
- Errors, warnings, or issues requiring user attention
- Completion or failure of background tasks (e.g., archiving, export)
- Progress updates for long-running tasks
- System or data changes affecting the user

## Choosing Notification Channel
- Use user preferences to determine channel: toast (in-app), email, or both
- Critical errors should default to both if user has not set a preference
- Use toast for immediate, transient feedback; email for persistent or out-of-app alerts

## Updating Notifications
- Use `transaction_id` to update progress/state of an existing notification instead of creating duplicates
- Only one notification per event/transaction should exist at a time
- Update `progress`, `pct_complete`, and `state` fields as the task advances

## Progress and State Best Practices
- Use `progress` for human-readable status (e.g., "Uploading file...", "50% complete")
- Use `pct_complete` for numeric progress (0-100)
- Use `state` for overall status: not started, in-progress, success, failed, etc.
- Always update the same notification for a transaction as state changes

## User Preferences
- Allow users to configure which notification classes trigger which channels
- Respect user preferences except for critical system errors (which may override)

## UI/UX
- Visually distinguish channel (icon/color)
- Show progress bar if `pct_complete` is present
- Show state as a badge (color-coded)
- Allow marking notifications as read
- Truncate long messages with tooltip for full text

## Audit and Logging
- Log all notification events and user responses for compliance and troubleshooting
- Include transaction_id, user_id, and state in logs

## Accessibility
- Ensure all notifications are accessible via screen readers
- Use sufficient color contrast for badges and progress bars

## Example
- Archiving starts: create notification (state: in-progress, progress: "Archiving started", pct_complete: 0)
- Archiving 50%: update same notification (state: in-progress, progress: "Halfway done", pct_complete: 50)
- Archiving complete: update notification (state: success, progress: "Archive complete", pct_complete: 100)
- Archiving failed: update notification (state: failed, progress: "Archive failed: [reason]", pct_complete: null) 