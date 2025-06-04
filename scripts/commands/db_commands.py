"""Database-related commands."""
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm

from scripts.utils.environment import get_project_root

console = Console()
db_app = typer.Typer(help="Database commands")

PROJECT_ROOT = get_project_root()


@db_app.command()
def init():
    """Initialize the core database."""
    console.print("[bold blue]Initializing core database...[/bold blue]")
    
    try:
        # Import and run the database initialization
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.core.db import Base, engine
        from src.core.models.appointment import Appointment
        # Import other core models as needed
        
        Base.metadata.create_all(bind=engine)
        console.print("[green]✅ Core database initialized successfully![/green]")
        return 0
    except Exception as e:
        console.print(f"[red]❌ Error initializing database: {e}[/red]")
        return 1


@db_app.command()
def migrate(
    message: str = typer.Option(None, "--message", "-m", help="Migration message"),
    autogenerate: bool = typer.Option(True, "--autogenerate/--no-autogenerate", help="Auto-generate migration"),
):
    """Create a new database migration."""
    console.print("[bold blue]Creating database migration...[/bold blue]")
    
    cmd = ['alembic', 'revision']
    
    if autogenerate:
        cmd.append('--autogenerate')
    
    if message:
        cmd.extend(['-m', message])
    else:
        cmd.extend(['-m', 'Auto-generated migration'])
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if result.returncode == 0:
            console.print("[green]✅ Migration created successfully![/green]")
        else:
            console.print("[red]❌ Error creating migration[/red]")
        return result.returncode
    except FileNotFoundError:
        console.print("[red]❌ Alembic not found. Install with: pip install alembic[/red]")
        return 1


@db_app.command()
def upgrade(
    revision: str = typer.Option("head", "--revision", "-r", help="Target revision"),
):
    """Upgrade database to a revision."""
    console.print(f"[bold blue]Upgrading database to {revision}...[/bold blue]")
    
    cmd = ['alembic', 'upgrade', revision]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if result.returncode == 0:
            console.print("[green]✅ Database upgraded successfully![/green]")
        else:
            console.print("[red]❌ Error upgrading database[/red]")
        return result.returncode
    except FileNotFoundError:
        console.print("[red]❌ Alembic not found. Install with: pip install alembic[/red]")
        return 1


@db_app.command()
def downgrade(
    revision: str = typer.Argument(..., help="Target revision"),
):
    """Downgrade database to a revision."""
    if not Confirm.ask(f"Are you sure you want to downgrade to {revision}?"):
        console.print("[yellow]Operation cancelled[/yellow]")
        return 0
    
    console.print(f"[bold blue]Downgrading database to {revision}...[/bold blue]")
    
    cmd = ['alembic', 'downgrade', revision]
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        if result.returncode == 0:
            console.print("[green]✅ Database downgraded successfully![/green]")
        else:
            console.print("[red]❌ Error downgrading database[/red]")
        return result.returncode
    except FileNotFoundError:
        console.print("[red]❌ Alembic not found. Install with: pip install alembic[/red]")
        return 1


@db_app.command()
def current():
    """Show current database revision."""
    console.print("[bold blue]Checking current database revision...[/bold blue]")
    
    cmd = ['alembic', 'current']
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode
    except FileNotFoundError:
        console.print("[red]❌ Alembic not found. Install with: pip install alembic[/red]")
        return 1


@db_app.command()
def history():
    """Show migration history."""
    console.print("[bold blue]Database migration history:[/bold blue]")
    
    cmd = ['alembic', 'history', '--verbose']
    
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode
    except FileNotFoundError:
        console.print("[red]❌ Alembic not found. Install with: pip install alembic[/red]")
        return 1


@db_app.command()
def reset():
    """Reset database (WARNING: This will delete all data!)."""
    if not Confirm.ask(
        "[red]This will delete ALL database data. Are you sure?[/red]",
        default=False
    ):
        console.print("[yellow]Operation cancelled[/yellow]")
        return 0
    
    console.print("[bold red]Resetting database...[/bold red]")
    
    # Remove database files
    instance_dir = PROJECT_ROOT / "instance"
    db_files = [
        instance_dir / "admin_assistant_core_dev.db",
        instance_dir / "admin_assistant_flask_dev.db",
    ]
    
    for db_file in db_files:
        if db_file.exists():
            try:
                db_file.unlink()
                console.print(f"[green]Removed {db_file.name}[/green]")
            except OSError as e:
                console.print(f"[red]Error removing {db_file.name}: {e}[/red]")
    
    # Reinitialize
    console.print("[blue]Reinitializing database...[/blue]")
    return init()


@db_app.command()
def backup(
    output_dir: Path = typer.Option(
        Path("backups"), 
        "--output", "-o", 
        help="Output directory for backup files"
    ),
):
    """Backup database files."""
    import shutil
    from datetime import datetime
    
    console.print("[bold blue]Creating database backup...[/bold blue]")
    
    # Create backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = output_dir / f"db_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup database files
    instance_dir = PROJECT_ROOT / "instance"
    db_files = [
        instance_dir / "admin_assistant_core_dev.db",
        instance_dir / "admin_assistant_flask_dev.db",
    ]
    
    backed_up = 0
    for db_file in db_files:
        if db_file.exists():
            try:
                backup_file = backup_dir / db_file.name
                shutil.copy2(db_file, backup_file)
                console.print(f"[green]✅ Backed up {db_file.name}[/green]")
                backed_up += 1
            except OSError as e:
                console.print(f"[red]❌ Error backing up {db_file.name}: {e}[/red]")
    
    if backed_up > 0:
        console.print(f"[green]✅ Backup completed: {backup_dir}[/green]")
        return 0
    else:
        console.print("[yellow]⚠️ No database files found to backup[/yellow]")
        return 1
