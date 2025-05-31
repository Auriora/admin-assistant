# Admin Assistant CLI

## CLI Usage

The Admin Assistant provides a powerful CLI for managing calendars, archives, and timesheet operations.

### Configuration Management

You can manage calendar archive configurations using the following commands:

```
# Archive calendar events using a specific config
admin-assistant calendar archive --user <USER_ID> --archive-config <CONFIG_ID> --date "last 7 days"

# List all archive configs for a user
admin-assistant config calendar archive list --user <USER_ID>

# Create a new archive config (interactive prompts for missing fields)
admin-assistant config calendar archive create --user <USER_ID>

# Create a new archive config (all options provided)
admin-assistant config calendar archive create --user <USER_ID> --name "Work Archive" --source-uri "msgraph://source" --dest-uri "msgraph://dest" --timezone "Europe/London" --active

# Activate/deactivate/delete a config
admin-assistant config calendar archive activate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive deactivate --user <USER_ID> --config-id <CONFIG_ID>
admin-assistant config calendar archive delete --user <USER_ID> --config-id <CONFIG_ID>

# Set a config as default (prints usage instructions)
admin-assistant config calendar archive set-default --user <USER_ID> --config-id <CONFIG_ID>
```