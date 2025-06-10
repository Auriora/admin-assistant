"""Common CLI options and parameters."""

from typing import Optional
import typer

# Common user option used across many commands
user_option = typer.Option(
    None,
    "--user",
    help="User to operate on (username or user ID). Falls back to ADMIN_ASSISTANT_USER env var, then OS username.",
    show_default=False,
)
