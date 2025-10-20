# Interactive Prompts User Guide

This guide explains how to use the interactive prompts feature, which allows you to run prompts with confirmation markers that pause execution and wait for user confirmation before continuing.

## Overview

Interactive prompts are templates with special markers (`<<AWAIT_CONFIRM: message>>`) that pause execution and wait for user confirmation before continuing. This is useful for complex workflows where you want to review and confirm each step before proceeding.

## Setup

Before using interactive prompts, you need to add at least one prompt template to the database. You can use the provided script to add a sample interactive prompt:

```bash
cd /path/to/admin-assistant
./scripts/add_sample_interactive_prompt.py
```

This script adds a sample "problem_solver" prompt template to the database for the first user it finds. The template includes multiple confirmation markers that pause execution at various points.

## Usage

To run an interactive prompt, use the `prompt run` command:

```bash
admin-assistant prompt run problem_solver --user <USER_ID>
```

Replace `<USER_ID>` with your user ID or email address.

The command will:
1. Display the initial content of the prompt up to the first confirmation marker
2. Pause and display the confirmation message
3. Wait for your confirmation (y/n)
4. If confirmed, continue to the next section of the prompt
5. Repeat until the entire prompt has been processed

You can cancel the interactive prompt at any time by answering "n" to a confirmation prompt.

## Creating Custom Interactive Prompts

You can create custom interactive prompts by adding new entries to the `prompts` table in the database. Each prompt should have:

- `prompt_type`: "action-specific"
- `user_id`: The ID of the user who can access this prompt
- `action_type`: A unique identifier for the prompt (e.g., "problem_solver", "researcher")
- `content`: The content of the prompt, including confirmation markers

Confirmation markers should be in the format `<<AWAIT_CONFIRM: message>>`, where `message` is the text to display when pausing for confirmation.

## Example

Here's a simple example of an interactive prompt:

```
This is the first part of the prompt.

<<AWAIT_CONFIRM: Ready to continue to the second part?>>

This is the second part of the prompt.

<<AWAIT_CONFIRM: Ready to continue to the final part?>>

This is the final part of the prompt.
```

When run, this prompt will:
1. Display "This is the first part of the prompt."
2. Pause and ask "Ready to continue to the second part?"
3. If confirmed, display "This is the second part of the prompt."
4. Pause and ask "Ready to continue to the final part?"
5. If confirmed, display "This is the final part of the prompt."

## Troubleshooting

If you encounter issues with interactive prompts:

- Make sure the prompt exists in the database for your user
- Check that the prompt content includes valid confirmation markers
- Verify that you're using the correct action_type in the command

For more help, contact your administrator or refer to the technical documentation.