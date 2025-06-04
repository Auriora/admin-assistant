"""Cleanup commands."""
from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from scripts.utils.paths import (
    get_build_artifacts, get_test_artifacts, get_python_cache,
    get_temp_files, get_node_artifacts, safe_remove_path
)

console = Console()
clean_app = typer.Typer(help="Cleanup commands")


def show_cleanup_summary(removed: List[Path], failed: List[Path]):
    """Show cleanup summary."""
    if removed or failed:
        table = Table(title="Cleanup Summary")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Details", style="yellow")
        
        if removed:
            table.add_row("✅ Removed", str(len(removed)), f"{len(removed)} items cleaned")
        
        if failed:
            table.add_row("❌ Failed", str(len(failed)), f"{len(failed)} items failed to clean")
        
        console.print(table)
        
        if failed:
            console.print("\n[red]Failed to remove:[/red]")
            for item in failed[:10]:  # Show first 10 failed items
                console.print(f"  [red]• {item}[/red]")
            if len(failed) > 10:
                console.print(f"  [red]... and {len(failed) - 10} more[/red]")
    else:
        console.print("[green]✅ Nothing to clean[/green]")


def clean_paths(paths: List[Path], description: str, confirm: bool = True) -> tuple[List[Path], List[Path]]:
    """Clean a list of paths."""
    if not paths:
        console.print(f"[green]✅ No {description} to clean[/green]")
        return [], []
    
    console.print(f"\n[bold blue]Found {len(paths)} {description}:[/bold blue]")
    for path in paths[:10]:  # Show first 10 items
        console.print(f"  • {path}")
    if len(paths) > 10:
        console.print(f"  ... and {len(paths) - 10} more")
    
    if confirm and not Confirm.ask(f"\nRemove {len(paths)} {description}?"):
        console.print("[yellow]Skipped[/yellow]")
        return [], []
    
    removed = []
    failed = []
    
    for path in paths:
        if safe_remove_path(path):
            removed.append(path)
        else:
            failed.append(path)
    
    return removed, failed


@clean_app.command()
def build(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Clean build artifacts."""
    console.print("[bold blue]🧹 Cleaning build artifacts...[/bold blue]")
    
    artifacts = get_build_artifacts()
    removed, failed = clean_paths(artifacts, "build artifacts", not force)
    show_cleanup_summary(removed, failed)
    
    return 0 if not failed else 1


@clean_app.command()
def test(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Clean test artifacts."""
    console.print("[bold blue]🧹 Cleaning test artifacts...[/bold blue]")
    
    artifacts = get_test_artifacts()
    removed, failed = clean_paths(artifacts, "test artifacts", not force)
    show_cleanup_summary(removed, failed)
    
    return 0 if not failed else 1


@clean_app.command()
def cache(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Clean Python cache files."""
    console.print("[bold blue]🧹 Cleaning Python cache...[/bold blue]")
    
    cache_files = list(get_python_cache())
    removed, failed = clean_paths(cache_files, "cache files", not force)
    show_cleanup_summary(removed, failed)
    
    return 0 if not failed else 1


@clean_app.command()
def temp(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Clean temporary files."""
    console.print("[bold blue]🧹 Cleaning temporary files...[/bold blue]")
    
    temp_files = get_temp_files()
    removed, failed = clean_paths(temp_files, "temporary files", not force)
    show_cleanup_summary(removed, failed)
    
    return 0 if not failed else 1


@clean_app.command()
def node(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Clean Node.js artifacts."""
    console.print("[bold blue]🧹 Cleaning Node.js artifacts...[/bold blue]")
    
    artifacts = get_node_artifacts()
    removed, failed = clean_paths(artifacts, "Node.js artifacts", not force)
    show_cleanup_summary(removed, failed)
    
    return 0 if not failed else 1


@clean_app.command()
def all(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Clean all artifacts and cache files."""
    console.print("[bold blue]🧹 Cleaning all artifacts...[/bold blue]")
    
    # Collect all artifacts
    all_artifacts = []
    all_artifacts.extend(get_build_artifacts())
    all_artifacts.extend(get_test_artifacts())
    all_artifacts.extend(list(get_python_cache()))
    all_artifacts.extend(get_temp_files())
    all_artifacts.extend(get_node_artifacts())
    
    # Remove duplicates while preserving order
    seen = set()
    unique_artifacts = []
    for artifact in all_artifacts:
        if artifact not in seen:
            seen.add(artifact)
            unique_artifacts.append(artifact)
    
    removed, failed = clean_paths(unique_artifacts, "artifacts", not force)
    show_cleanup_summary(removed, failed)
    
    return 0 if not failed else 1


@clean_app.command("list")
def list_artifacts():
    """List all cleanable artifacts without removing them."""
    console.print("[bold blue]📋 Cleanable artifacts:[/bold blue]")

    categories = [
        ("Build artifacts", get_build_artifacts()),
        ("Test artifacts", get_test_artifacts()),
        ("Python cache", [p for p in get_python_cache()]),
        ("Temporary files", get_temp_files()),
        ("Node.js artifacts", get_node_artifacts()),
    ]
    
    table = Table(title="Cleanable Artifacts")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="green")
    table.add_column("Examples", style="yellow")
    
    total_count = 0
    for category, artifacts in categories:
        count = len(artifacts)
        total_count += count
        
        if count > 0:
            examples = ", ".join(str(p.name) for p in artifacts[:3])
            if count > 3:
                examples += f" ... (+{count - 3} more)"
        else:
            examples = "None"
        
        table.add_row(category, str(count), examples)
    
    table.add_row("", "", "", style="dim")
    table.add_row("Total", str(total_count), "", style="bold")
    
    console.print(table)
    
    if total_count > 0:
        console.print(f"\n[blue]💡 Run 'dev-cli clean all' to remove all {total_count} items[/blue]")
    else:
        console.print("\n[green]✅ No artifacts to clean[/green]")
