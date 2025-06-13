"""
Custom Click Group class that shows help when commands are not found.

This provides a better user experience by showing available commands
when a user makes a typo, instead of just showing an error message.
"""

import click
import typer
from typer.core import TyperGroup
from rich.console import Console
from rich.panel import Panel


class HelpfulGroup(TyperGroup):
    """
    A Click Group that shows help when a command is not found.
    
    When a user types a command that doesn't exist (like a typo),
    instead of showing just an error message, this will display
    the help for the parent command showing all available commands.
    """
    
    def resolve_command(self, ctx, args):
        """
        Resolve a command name to a command object.

        If the command is not found, show the error message and help.
        """
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as e:
            # Check if this is a "No such command" error
            error_message = str(e)
            if "No such command" in error_message:
                self._show_error_and_help(ctx, error_message)
            else:
                # Re-raise other usage errors (like missing arguments)
                raise

    def invoke(self, ctx):
        """
        Invoke the command.

        If no subcommand is provided, show error and help.
        """
        try:
            return super().invoke(ctx)
        except click.UsageError as e:
            # Check if this is a "Missing command" error
            error_message = str(e)
            if "Missing command" in error_message:
                self._show_error_and_help(ctx, error_message)
            else:
                # Re-raise other usage errors
                raise

    def _show_error_and_help(self, ctx, error_message):
        """
        Show error message in rich format and then help.
        """
        # Create a console for rich formatting
        console = Console(stderr=True)

        # Show the error message in Typer's rich format
        error_panel = Panel(
            error_message,
            title="Error",
            title_align="left",
            border_style="red",
            padding=(0, 1)
        )
        console.print(error_panel)
        typer.echo()  # Add a blank line for readability

        # Then show help
        typer.echo(ctx.get_help())
        ctx.exit(2)  # Use exit code 2 to indicate error
