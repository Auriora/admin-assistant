"""Version management commands."""
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from scripts.utils.environment import get_project_root

console = Console()
version_app = typer.Typer(help="Version management commands")

PROJECT_ROOT = get_project_root()


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject_file = PROJECT_ROOT / "pyproject.toml"
    
    if not pyproject_file.exists():
        return "unknown"
    
    try:
        # Try tomllib first (Python 3.11+)
        import tomllib
        with open(pyproject_file, "rb") as f:
            data = tomllib.load(f)
            return data.get("project", {}).get("version", "unknown")
    except ImportError:
        try:
            # Fallback to tomli
            import tomli
            with open(pyproject_file, "rb") as f:
                data = tomli.load(f)
                return data.get("project", {}).get("version", "unknown")
        except ImportError:
            # Manual parsing as last resort
            with open(pyproject_file, "r") as f:
                for line in f:
                    if line.strip().startswith('version = '):
                        # Extract version from line like: version = "0.1.0alpha1"
                        return line.split('"')[1]
            return "unknown"


def run_bumpversion_command(cmd: list[str], description: str) -> int:
    """Run a bumpversion command."""
    try:
        console.print(f"[blue]{description}...[/blue]")
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print(f"[green]✅ {description} completed successfully![/green]")
            if result.stdout:
                console.print(result.stdout)
        else:
            console.print(f"[red]❌ {description} failed[/red]")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
        
        return result.returncode
    except FileNotFoundError:
        console.print("[red]❌ bumpversion not found. Install with: pip install bump2version[/red]")
        return 1


@version_app.command()
def show():
    """Show current version information."""
    console.print("[bold blue]📋 Version Information:[/bold blue]")
    
    current_version = get_current_version()
    
    table = Table(title="Version Details")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Current Version", current_version)
    
    # Check if bumpversion config exists
    bumpversion_config = PROJECT_ROOT / ".bumpversion.cfg"
    if bumpversion_config.exists():
        table.add_row("Bumpversion Config", "✅ Available")
        
        # Try to get version from bumpversion config
        try:
            with open(bumpversion_config, "r") as f:
                for line in f:
                    if line.strip().startswith("current_version"):
                        config_version = line.split("=")[1].strip()
                        table.add_row("Config Version", config_version)
                        break
        except Exception:
            pass
    else:
        table.add_row("Bumpversion Config", "❌ Missing")
    
    # Check git status
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            table.add_row("Git Describe", result.stdout.strip())
    except subprocess.CalledProcessError:
        pass
    
    console.print(table)


@version_app.command()
def bump(
    part: str = typer.Argument(..., help="Version part to bump (major, minor, patch, release, num)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done without making changes"),
    tag: bool = typer.Option(True, "--tag/--no-tag", help="Create git tag"),
    commit: bool = typer.Option(True, "--commit/--no-commit", help="Create git commit"),
):
    """Bump version using bumpversion."""
    valid_parts = ["major", "minor", "patch", "release", "num"]
    
    if part not in valid_parts:
        console.print(f"[red]❌ Invalid part '{part}'. Valid parts: {', '.join(valid_parts)}[/red]")
        return 1
    
    current_version = get_current_version()
    console.print(f"[blue]Current version: {current_version}[/blue]")
    
    cmd = ['bumpversion']
    
    if dry_run:
        cmd.append('--dry-run')
        cmd.append('--verbose')
    
    if not tag:
        cmd.append('--no-tag')
    
    if not commit:
        cmd.append('--no-commit')
    
    cmd.append(part)
    
    description = f"Bump {part} version"
    if dry_run:
        description += " (dry run)"
    
    result = run_bumpversion_command(cmd, description)
    
    if result == 0 and not dry_run:
        new_version = get_current_version()
        console.print(f"[green]Version bumped: {current_version} → {new_version}[/green]")
    
    return result


@version_app.command()
def tag(
    version: str = typer.Option(None, "--version", "-v", help="Version to tag (default: current version)"),
    message: str = typer.Option(None, "--message", "-m", help="Tag message"),
    push: bool = typer.Option(False, "--push", help="Push tag to remote"),
):
    """Create a git tag for the current or specified version."""
    if version is None:
        version = get_current_version()
        if version == "unknown":
            console.print("[red]❌ Cannot determine current version[/red]")
            return 1
    
    # Ensure version starts with 'v'
    if not version.startswith('v'):
        tag_name = f"v{version}"
    else:
        tag_name = version
    
    if message is None:
        message = f"Release {version}"
    
    console.print(f"[blue]Creating tag: {tag_name}[/blue]")
    
    try:
        # Create tag
        cmd = ['git', 'tag', '-a', tag_name, '-m', message]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
        if result.returncode == 0:
            console.print(f"[green]✅ Tag {tag_name} created successfully![/green]")
            
            if push:
                console.print("[blue]Pushing tag to remote...[/blue]")
                push_cmd = ['git', 'push', 'origin', tag_name]
                push_result = subprocess.run(push_cmd, cwd=PROJECT_ROOT)
                
                if push_result.returncode == 0:
                    console.print("[green]✅ Tag pushed to remote![/green]")
                else:
                    console.print("[red]❌ Failed to push tag to remote[/red]")
                    return push_result.returncode
        else:
            console.print("[red]❌ Failed to create tag[/red]")
            return result.returncode
        
        return 0
    except FileNotFoundError:
        console.print("[red]❌ Git not found[/red]")
        return 1


@version_app.command()
def history():
    """Show version history from git tags."""
    console.print("[bold blue]📋 Version History:[/bold blue]")
    
    try:
        # Get all tags sorted by version
        result = subprocess.run(
            ['git', 'tag', '--sort=-version:refname'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            tags = result.stdout.strip().split('\n')
            tags = [tag for tag in tags if tag]  # Remove empty strings
            
            if not tags:
                console.print("[yellow]No version tags found[/yellow]")
                return 0
            
            table = Table(title="Version Tags")
            table.add_column("Tag", style="cyan")
            table.add_column("Date", style="green")
            table.add_column("Commit", style="yellow")
            
            for tag in tags[:10]:  # Show last 10 tags
                try:
                    # Get tag date and commit
                    tag_info = subprocess.run(
                        ['git', 'log', '-1', '--format=%ci %h', tag],
                        cwd=PROJECT_ROOT,
                        capture_output=True,
                        text=True
                    )
                    
                    if tag_info.returncode == 0:
                        parts = tag_info.stdout.strip().split()
                        date = parts[0] if parts else "unknown"
                        commit = parts[-1] if len(parts) > 1 else "unknown"
                        table.add_row(tag, date, commit)
                    else:
                        table.add_row(tag, "unknown", "unknown")
                except subprocess.CalledProcessError:
                    table.add_row(tag, "unknown", "unknown")
            
            console.print(table)
            
            if len(tags) > 10:
                console.print(f"[blue]... and {len(tags) - 10} more tags[/blue]")
        else:
            console.print("[red]❌ Failed to get git tags[/red]")
            return result.returncode
        
        return 0
    except FileNotFoundError:
        console.print("[red]❌ Git not found[/red]")
        return 1


@version_app.command()
def check():
    """Check version consistency across files."""
    console.print("[bold blue]🔍 Checking version consistency...[/bold blue]")
    
    versions = {}
    
    # Get version from pyproject.toml
    pyproject_version = get_current_version()
    versions["pyproject.toml"] = pyproject_version
    
    # Get version from bumpversion config
    bumpversion_config = PROJECT_ROOT / ".bumpversion.cfg"
    if bumpversion_config.exists():
        try:
            with open(bumpversion_config, "r") as f:
                for line in f:
                    if line.strip().startswith("current_version"):
                        config_version = line.split("=")[1].strip()
                        versions[".bumpversion.cfg"] = config_version
                        break
        except Exception:
            versions[".bumpversion.cfg"] = "error reading file"
    
    # Display results
    table = Table(title="Version Consistency Check")
    table.add_column("File", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Status", style="yellow")
    
    reference_version = pyproject_version
    all_consistent = True
    
    for file, version in versions.items():
        if version == reference_version:
            status = "✅ Consistent"
        else:
            status = "❌ Inconsistent"
            all_consistent = False
        
        table.add_row(file, version, status)
    
    console.print(table)
    
    if all_consistent:
        console.print("[green]✅ All versions are consistent![/green]")
        return 0
    else:
        console.print("[red]❌ Version inconsistencies found![/red]")
        console.print("[blue]💡 Run 'dev-cli version bump patch --dry-run' to see what would be updated[/blue]")
        return 1
