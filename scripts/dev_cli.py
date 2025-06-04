#!/usr/bin/env python3
"""
Development CLI for the admin-assistant project.
Provides unified access to all development and build helper scripts.
"""
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.commands.test_commands import test_app
from scripts.commands.db_commands import db_app
from scripts.commands.build_commands import build_app
from scripts.commands.version_commands import version_app
from scripts.commands.clean_commands import clean_app

console = Console()

# Create main CLI app
app = typer.Typer(
    name="dev-cli",
    help="Development CLI for admin-assistant project",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Add command groups
app.add_typer(test_app, name="test", help="Testing commands")
app.add_typer(db_app, name="db", help="Database commands")
app.add_typer(build_app, name="build", help="Build and packaging commands")
app.add_typer(version_app, name="version", help="Version management commands")
app.add_typer(clean_app, name="clean", help="Cleanup commands")


@app.callback()
def main():
    """
    Development CLI for admin-assistant project.
    
    Provides unified access to testing, database, build, version, and cleanup commands.
    """
    pass


@app.command()
def info():
    """Show development environment information."""
    from scripts.utils.environment import show_environment_info
    show_environment_info()


if __name__ == "__main__":
    app()
