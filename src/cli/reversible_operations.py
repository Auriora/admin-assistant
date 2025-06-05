"""
CLI commands for managing reversible operations.
"""

import typer
from typing import Optional
from datetime import date, datetime

from core.db import get_session
from core.services.reversible_audit_service import ReversibleAuditService
from core.services.user_service import UserService
from core.utilities.user_resolution import resolve_user, get_user_identifier_source

# Create the reversible operations app
reversible_app = typer.Typer(help="Manage reversible operations and audit logs")


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


@reversible_app.command("list")
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
            typer.echo("No reversible operations found.")
            return
        
        # Display operations
        typer.echo(f"\n[bold]Reversible Operations for {user.email}[/bold]")
        typer.echo("=" * 60)
        
        for op in operations:
            status_color = "green" if op.is_reversed else ("red" if not op.is_reversible else "yellow")
            status_text = "REVERSED" if op.is_reversed else ("NOT REVERSIBLE" if not op.is_reversible else "REVERSIBLE")
            
            typer.echo(f"\n[bold]ID:[/bold] {op.id}")
            typer.echo(f"[bold]Operation:[/bold] {op.operation_name}")
            typer.echo(f"[bold]Type:[/bold] {op.operation_type}")
            typer.echo(f"[bold]Status:[/bold] [{status_color}]{status_text}[/{status_color}]")
            typer.echo(f"[bold]Created:[/bold] {op.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            if op.is_reversed:
                typer.echo(f"[bold]Reversed:[/bold] {op.reversed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                typer.echo(f"[bold]Reason:[/bold] {op.reverse_reason}")
            
            if not op.is_reversible and op.reverse_reason:
                typer.echo(f"[bold]Not Reversible:[/bold] {op.reverse_reason}")
            
            # Show item count
            item_count = len(op.items) if op.items else 0
            typer.echo(f"[bold]Items:[/bold] {item_count}")
            
            if op.correlation_id:
                typer.echo(f"[bold]Correlation ID:[/bold] {op.correlation_id}")
        
        session.close()
        
    except Exception as e:
        typer.echo(f"[red]Error listing operations: {e}[/red]")
        raise typer.Exit(code=1)


@reversible_app.command("show")
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
            typer.echo(f"[red]Operation {operation_id} not found.[/red]")
            raise typer.Exit(code=1)
        
        # Check if user has permission to view this operation
        if operation.user_id != user.id:
            typer.echo(f"[red]You don't have permission to view operation {operation_id}.[/red]")
            raise typer.Exit(code=1)
        
        # Display detailed operation info
        typer.echo(f"\n[bold]Operation {operation.id} Details[/bold]")
        typer.echo("=" * 50)
        
        typer.echo(f"[bold]Operation Name:[/bold] {operation.operation_name}")
        typer.echo(f"[bold]Type:[/bold] {operation.operation_type}")
        typer.echo(f"[bold]Created:[/bold] {operation.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        typer.echo(f"[bold]Reversible:[/bold] {'Yes' if operation.is_reversible else 'No'}")
        typer.echo(f"[bold]Reversed:[/bold] {'Yes' if operation.is_reversed else 'No'}")
        
        if operation.is_reversed:
            typer.echo(f"[bold]Reversed At:[/bold] {operation.reversed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            typer.echo(f"[bold]Reversed By:[/bold] User {operation.reversed_by_user_id}")
            typer.echo(f"[bold]Reverse Reason:[/bold] {operation.reverse_reason}")
        
        if not operation.is_reversible and operation.reverse_reason:
            typer.echo(f"[bold]Not Reversible Reason:[/bold] {operation.reverse_reason}")
        
        if operation.correlation_id:
            typer.echo(f"[bold]Correlation ID:[/bold] {operation.correlation_id}")
        
        # Show items
        if operation.items:
            typer.echo(f"\n[bold]Items ({len(operation.items)}):[/bold]")
            for i, item in enumerate(operation.items, 1):
                item_status = "REVERSED" if item.is_reversed else "NOT REVERSED"
                typer.echo(f"  {i}. {item.item_type} {item.item_id} - {item.reverse_action.upper()} - {item_status}")
                if item.reverse_error:
                    typer.echo(f"     [red]Error: {item.reverse_error}[/red]")
        
        # Show dependencies
        if operation.depends_on_operations:
            typer.echo(f"\n[bold]Depends On:[/bold] {', '.join(map(str, operation.depends_on_operations))}")
        
        if operation.blocks_operations:
            typer.echo(f"[bold]Blocks:[/bold] {', '.join(map(str, operation.blocks_operations))}")
        
        session.close()
        
    except Exception as e:
        typer.echo(f"[red]Error showing operation: {e}[/red]")
        raise typer.Exit(code=1)


@reversible_app.command("reverse")
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
            typer.echo(f"[red]Operation {operation_id} not found.[/red]")
            raise typer.Exit(code=1)
        
        # Check if user has permission to reverse this operation
        if operation.user_id != user.id:
            typer.echo(f"[red]You don't have permission to reverse operation {operation_id}.[/red]")
            raise typer.Exit(code=1)
        
        # Show operation details
        typer.echo(f"\n[bold]Operation to Reverse:[/bold]")
        typer.echo(f"ID: {operation.id}")
        typer.echo(f"Name: {operation.operation_name}")
        typer.echo(f"Type: {operation.operation_type}")
        typer.echo(f"Created: {operation.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        typer.echo(f"Items: {len(operation.items) if operation.items else 0}")
        
        if dry_run:
            typer.echo(f"\n[yellow]DRY RUN MODE - No changes will be made[/yellow]")
        
        # Check if operation can be reversed
        can_reverse, blocking_reasons = reversible_service.check_operation_dependencies(operation)
        if not can_reverse:
            typer.echo(f"\n[red]Cannot reverse operation:[/red]")
            for reason in blocking_reasons:
                typer.echo(f"  - {reason}")
            raise typer.Exit(code=1)
        
        # Confirm reversal (unless dry run)
        if not dry_run:
            typer.echo(f"\n[yellow]WARNING: This will reverse the operation and all its effects.[/yellow]")
            typer.echo(f"[yellow]Reason: {reason}[/yellow]")
            
            if not typer.confirm("Are you sure you want to proceed?"):
                typer.echo("Operation cancelled.")
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
                typer.echo(f"\n[green]DRY RUN: Operation can be safely reversed[/green]")
                typer.echo(f"Items to reverse: {result['items_to_reverse']}")
                typer.echo(f"Reverse actions: {', '.join(result['reverse_actions'])}")
            else:
                typer.echo(f"\n[green]Operation reversed successfully![/green]")
                typer.echo(f"Reversed items: {result['reversed_items']}")
                if result['failed_items'] > 0:
                    typer.echo(f"[yellow]Failed items: {result['failed_items']}[/yellow]")
                    for error in result['errors']:
                        typer.echo(f"  [red]Error: {error}[/red]")
        else:
            typer.echo(f"\n[red]Failed to reverse operation: {result.get('error', 'Unknown error')}[/red]")
            if 'reasons' in result:
                for reason in result['reasons']:
                    typer.echo(f"  - {reason}")
        
        session.close()
        
    except Exception as e:
        typer.echo(f"[red]Error reversing operation: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    reversible_app()
