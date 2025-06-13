"""
CLI commands for interactive prompts with confirmation markers.
"""

import typer
from typing import Optional

from cli.common.helpful_group import HelpfulGroup

from core.db import get_session
from core.services.interactive_prompt_service import InteractivePromptService
from core.services.user_service import UserService
from core.utilities.user_resolution import resolve_user, get_user_identifier_source

# Create the interactive prompt app
interactive_prompt_app = typer.Typer(help="Interactive prompts with confirmation markers", rich_markup_mode="rich", cls=HelpfulGroup)


@interactive_prompt_app.callback()
def prompt_callback(ctx: typer.Context):
    """Interactive prompt system commands.

    Run interactive prompts for various tasks.
    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def resolve_cli_user(cli_user_input: Optional[str] = None):
    """
    Resolve user from CLI input with proper error handling.
    """
    try:
        user = resolve_user(cli_user_input)
        if not user:
            source = get_user_identifier_source(cli_user_input)
            typer.echo(f"No user identifier found from {source}.")
            typer.echo(
                "Please specify --user <username_or_id> or set ADMIN_ASSISTANT_USER environment variable."
            )
            raise typer.Exit(code=1)
        return user
    except ValueError as e:
        source = get_user_identifier_source(cli_user_input)
        typer.echo(f"Error resolving user from {source}: {e}")
        raise typer.Exit(code=1)


@interactive_prompt_app.command("run")
def run_interactive_prompt(
    prompt_type: str = typer.Argument(
        ...,
        help="Type of prompt to run (e.g., 'problem_solver', 'researcher')",
    ),
    user_input: Optional[str] = typer.Option(
        None,
        "--user",
        help="User to run prompt for (username or user ID). Falls back to ADMIN_ASSISTANT_USER env var, then OS username.",
    ),
):
    """
    Run an interactive prompt with confirmation markers.

    This command processes a prompt template with <<AWAIT_CONFIRM>> markers,
    pausing at each marker to wait for user confirmation before continuing.
    """
    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get session and service
        session = get_session()
        interactive_prompt_service = InteractivePromptService(session)

        # Get the interactive prompt
        prompt, content, needs_confirmation, confirmation_message = interactive_prompt_service.get_interactive_prompt(
            user_id=user.id,
            action_type=prompt_type
        )

        if not prompt:
            typer.echo(f"No prompt found for type '{prompt_type}'.")
            return

        # Display the initial content
        typer.echo(content)

        # Process the prompt interactively
        prompt_content = getattr(prompt, "content", "")
        while needs_confirmation:
            # Display the confirmation message
            typer.echo(f"\n[bold]<<AWAIT_CONFIRM: {confirmation_message}>>[/bold]")

            # Wait for user confirmation
            if not typer.confirm("Continue?"):
                typer.echo("Interactive prompt cancelled.")
                return

            # Continue after confirmation
            next_content, needs_confirmation, confirmation_message = interactive_prompt_service.continue_after_confirmation(prompt_content)

            # Display the next content
            typer.echo(next_content)

        # Display completion message
        typer.echo("\n[bold]Interactive prompt completed.[/bold]")

        session.close()

    except Exception as e:
        typer.echo(f"[red]Error running interactive prompt: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    interactive_prompt_app()
