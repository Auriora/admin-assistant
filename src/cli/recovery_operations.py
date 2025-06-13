"""
CLI commands for managing reversible operations.
"""

import typer
from typing import Optional
from datetime import date, datetime
from rich.console import Console
from rich.table import Table

from core.db import get_session
from core.services.reversible_audit_service import ReversibleAuditService
from core.services.user_service import UserService
from core.utilities.user_resolution import resolve_user, get_user_identifier_source

# Create console for rich output
console = Console()

# Create the recovery operations app
recovery_app = typer.Typer(
    help="Manage reversible operations and audit logs",
    rich_markup_mode="rich"
)


@recovery_app.callback()
def recovery_callback(ctx: typer.Context):
    """Recovery operations management commands.

    Manage and reverse completed operations.
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
            console.print(f"No user identifier found from {source}.")
            console.print(
                "Please specify --user <username_or_id> or set ADMIN_ASSISTANT_USER environment variable."
            )
            raise typer.Exit(code=1)
        return user
    except ValueError as e:
        source = get_user_identifier_source(cli_user_input)
        console.print(f"Error resolving user from {source}: {e}")
        raise typer.Exit(code=1)


@recovery_app.command("list")
def list_operations(
    user_input: Optional[str] = typer.Option(
        None,
        "--user",
        help="User to list operations for (username or user ID). Falls back to ADMIN_ASSISTANT_USER env var, then OS username.",
    ),
    operation_type: Optional[str] = typer.Option(
        None,
        "--type",
        help="Filter by operation type (e.g., 'archive_replace', 'delete')",
    ),
    is_reversed: Optional[bool] = typer.Option(
        None,
        "--reversed",
        help="Filter by reversal status (true for reversed, false for not reversed)",
    ),
    limit: Optional[int] = typer.Option(
        10,
        "--limit",
        help="Maximum number of operations to show",
    ),
):
    """List reversible operations for a user."""
    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get operations
        session = get_session()
        reversible_service = ReversibleAuditService(session)

        operations = reversible_service.get_reversible_operations(
            user_id=user.id,
            operation_type=operation_type,
            is_reversed=is_reversed,
            limit=limit,
        )

        if not operations:
            console.print("No reversible operations found.")
            return

        # Display operations in a table
        table = Table(title=f"Reversible Operations for {user.email}")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Operation", style="green")
        table.add_column("Type", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="magenta")
        table.add_column("Items", style="cyan", justify="right")
        table.add_column("Correlation ID", style="dim")

        for op in operations:
            status_color = "yellow" if op.is_reversible and not op.is_reversed else "red"
            status_text = "REVERSIBLE" if op.is_reversible and not op.is_reversed else "NOT REVERSIBLE"

            # Format the status with color
            status = f"[{status_color}]{status_text}[/{status_color}]"

            # Get reason if not reversible
            if not op.is_reversible and op.reverse_reason:
                status += f"\n({op.reverse_reason})"

            # Show item count
            item_count = len(op.items) if op.items else 0

            # Add row to table
            table.add_row(
                str(op.id),
                op.operation_name,
                op.operation_type,
                status,
                op.created_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                str(item_count),
                op.correlation_id or ""
            )

        # Print the table
        console.print(table)

        session.close()

    except Exception as e:
        console.print(f"[red]Error listing operations: {e}[/red]")
        raise typer.Exit(code=1)


@recovery_app.command("show")
def show_operation(
    operation_id: int = typer.Argument(..., help="ID of the operation to show"),
    user_input: Optional[str] = typer.Option(
        None,
        "--user",
        help="User (for permission checking)",
    ),
):
    """Show detailed information about a specific reversible operation."""
    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get operation
        session = get_session()
        reversible_service = ReversibleAuditService(session)

        operation = reversible_service.get_operation_by_id(operation_id)
        if not operation:
            console.print(f"[red]Operation {operation_id} not found.[/red]")
            raise typer.Exit(code=1)

        # Check if user has permission to view this operation
        if operation.user_id != user.id:
            console.print(f"[red]You don't have permission to view operation {operation_id}.[/red]")
            raise typer.Exit(code=1)

        # Display detailed operation info
        console.print(f"\n[bold]Operation {operation.id} Details[/bold]")
        console.print("=" * 50)

        console.print(f"[bold]Operation Name:[/bold] {operation.operation_name}")
        console.print(f"[bold]Type:[/bold] {operation.operation_type}")
        console.print(f"[bold]Created:[/bold] {operation.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        console.print(f"[bold]Reversible:[/bold] {'Yes' if operation.is_reversible else 'No'}")
        console.print(f"[bold]Reversed:[/bold] {'Yes' if operation.is_reversed else 'No'}")

        if operation.is_reversed:
            console.print(f"[bold]Reversed At:[/bold] {operation.reversed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            console.print(f"[bold]Reversed By:[/bold] User {operation.reversed_by_user_id}")
            console.print(f"[bold]Reverse Reason:[/bold] {operation.reverse_reason}")

        if not operation.is_reversible and operation.reverse_reason:
            console.print(f"[bold]Not Reversible Reason:[/bold] {operation.reverse_reason}")

        if operation.correlation_id:
            console.print(f"[bold]Correlation ID:[/bold] {operation.correlation_id}")

        # Show items
        if operation.items:
            console.print(f"\n[bold]Items ({len(operation.items)}):[/bold]")
            for i, item in enumerate(operation.items, 1):
                item_status = "REVERSED" if item.is_reversed else "NOT REVERSED"
                console.print(f"  {i}. {item.item_type} {item.item_id} - {item.reverse_action.upper()} - {item_status}")
                if item.reverse_error:
                    console.print(f"     [red]Error: {item.reverse_error}[/red]")

        # Show dependencies
        if operation.depends_on_operations:
            console.print(f"\n[bold]Depends On:[/bold] {', '.join(map(str, operation.depends_on_operations))}")

        if operation.blocks_operations:
            console.print(f"[bold]Blocks:[/bold] {', '.join(map(str, operation.blocks_operations))}")

        session.close()

    except Exception as e:
        console.print(f"[red]Error showing operation: {e}[/red]")
        raise typer.Exit(code=1)


@recovery_app.command("reverse")
def reverse_operation(
    operation_id: int = typer.Argument(..., help="ID of the operation to reverse"),
    reason: str = typer.Option(
        ...,
        "--reason",
        help="Reason for reversing the operation",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be reversed without actually doing it",
    ),
    user_input: Optional[str] = typer.Option(
        None,
        "--user",
        help="User performing the reversal",
    ),
):
    """Reverse a completed operation."""
    try:
        # Get user
        user = resolve_cli_user(user_input)

        # Get operation
        session = get_session()
        reversible_service = ReversibleAuditService(session)

        operation = reversible_service.get_operation_by_id(operation_id)
        if not operation:
            console.print(f"[red]Operation {operation_id} not found.[/red]")
            raise typer.Exit(code=1)

        # Check if user has permission to reverse this operation
        if operation.user_id != user.id:
            console.print(f"[red]You don't have permission to reverse operation {operation_id}.[/red]")
            raise typer.Exit(code=1)

        # Show operation details
        console.print(f"\n[bold]Operation to Reverse:[/bold]")
        console.print(f"ID: {operation.id}")
        console.print(f"Name: {operation.operation_name}")
        console.print(f"Type: {operation.operation_type}")
        console.print(f"Created: {operation.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        console.print(f"Items: {len(operation.items) if operation.items else 0}")

        if dry_run:
            console.print(f"\n[yellow]DRY RUN MODE - No changes will be made[/yellow]")

        # Check if operation can be reversed
        can_reverse, blocking_reasons = reversible_service.check_operation_dependencies(operation)
        if not can_reverse:
            console.print(f"\n[red]Cannot reverse operation:[/red]")
            for reason in blocking_reasons:
                console.print(f"  - {reason}")
            raise typer.Exit(code=1)

        # Confirm reversal (unless dry run)
        if not dry_run:
            console.print(f"\n[yellow]WARNING: This will reverse the operation and all its effects.[/yellow]")
            console.print(f"[yellow]Reason: {reason}[/yellow]")

            if not typer.confirm("Are you sure you want to proceed?"):
                console.print("Operation cancelled.")
                raise typer.Exit(code=0)

        # Perform the reversal
        result = reversible_service.reverse_operation(
            operation_id=operation_id,
            reversed_by_user_id=user.id,
            reason=reason,
            dry_run=dry_run,
        )

        if result["success"]:
            if dry_run:
                console.print(f"\n[green]DRY RUN: Operation can be safely reversed[/green]")
                console.print(f"Items to reverse: {result['items_to_reverse']}")
                console.print(f"Reverse actions: {', '.join(result['reverse_actions'])}")
            else:
                console.print(f"\n[green]Operation reversed successfully![/green]")
                console.print(f"Reversed items: {result['reversed_items']}")
                if result['failed_items'] > 0:
                    console.print(f"[yellow]Failed items: {result['failed_items']}[/yellow]")
                    for error in result['errors']:
                        console.print(f"  [red]Error: {error}[/red]")
        else:
            console.print(f"\n[red]Failed to reverse operation: {result.get('error', 'Unknown error')}[/red]")
            if 'reasons' in result:
                for reason in result['reasons']:
                    console.print(f"  - {reason}")

        session.close()

    except Exception as e:
        console.print(f"[red]Error reversing operation: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    recovery_app()
