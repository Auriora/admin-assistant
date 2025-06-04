"""Build and packaging commands."""
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from scripts.utils.environment import get_project_root, check_virtual_environment
from scripts.utils.paths import get_build_artifacts, safe_remove_path

console = Console()
build_app = typer.Typer(help="Build and packaging commands")

PROJECT_ROOT = get_project_root()


def run_build_command(cmd: list[str], description: str) -> int:
    """Run a build command with progress indication."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(description, total=None)
        
        try:
            result = subprocess.run(cmd, cwd=PROJECT_ROOT)
            progress.update(task, completed=True)
            return result.returncode
        except KeyboardInterrupt:
            console.print("\n[red]Build interrupted by user[/red]")
            return 130
        except Exception as e:
            console.print(f"\n[red]Error during build: {e}[/red]")
            return 1


@build_app.command()
def package(
    clean_first: bool = typer.Option(True, "--clean/--no-clean", help="Clean build artifacts first"),
    wheel: bool = typer.Option(True, "--wheel/--no-wheel", help="Build wheel package"),
    sdist: bool = typer.Option(True, "--sdist/--no-sdist", help="Build source distribution"),
):
    """Build package distributions."""
    console.print("[bold blue]📦 Building package...[/bold blue]")
    
    if not check_virtual_environment():
        console.print("[yellow]⚠️ Virtual environment not detected. Consider activating .venv[/yellow]")
    
    # Clean first if requested
    if clean_first:
        console.print("[blue]Cleaning build artifacts...[/blue]")
        artifacts = get_build_artifacts()
        for artifact in artifacts:
            safe_remove_path(artifact)
    
    # Build command
    cmd = ['python', '-m', 'build']
    
    if not wheel and not sdist:
        console.print("[red]❌ Must build at least one of wheel or sdist[/red]")
        return 1
    
    if wheel and not sdist:
        cmd.append('--wheel')
    elif sdist and not wheel:
        cmd.append('--sdist')
    # If both are True (default), build both
    
    try:
        result = run_build_command(cmd, "Building package")
        
        if result == 0:
            console.print("[green]✅ Package built successfully![/green]")
            
            # Show built files
            dist_dir = PROJECT_ROOT / "dist"
            if dist_dir.exists():
                built_files = list(dist_dir.glob("*"))
                if built_files:
                    console.print("\n[blue]Built files:[/blue]")
                    for file in built_files:
                        console.print(f"  • {file.name}")
        else:
            console.print("[red]❌ Package build failed[/red]")
        
        return result
    except FileNotFoundError:
        console.print("[red]❌ Build tool not found. Install with: pip install build[/red]")
        return 1


@build_app.command()
def install(
    editable: bool = typer.Option(True, "--editable/--no-editable", help="Install in editable mode"),
    dev: bool = typer.Option(True, "--dev/--no-dev", help="Install development dependencies"),
):
    """Install the package in the current environment."""
    console.print("[bold blue]📦 Installing package...[/bold blue]")
    
    if not check_virtual_environment():
        console.print("[yellow]⚠️ Virtual environment not detected. Consider activating .venv[/yellow]")
    
    cmd = ['pip', 'install']
    
    if editable:
        cmd.append('-e')
    
    if dev:
        cmd.append('.[dev]')
    else:
        cmd.append('.')
    
    result = run_build_command(cmd, "Installing package")
    
    if result == 0:
        console.print("[green]✅ Package installed successfully![/green]")
    else:
        console.print("[red]❌ Package installation failed[/red]")
    
    return result


@build_app.command()
def check():
    """Check package metadata and distribution."""
    console.print("[bold blue]🔍 Checking package...[/bold blue]")
    
    # Check with twine if available
    try:
        cmd = ['twine', 'check', 'dist/*']
        result = run_build_command(cmd, "Checking package with twine")
        
        if result == 0:
            console.print("[green]✅ Package check passed![/green]")
        else:
            console.print("[red]❌ Package check failed[/red]")
        
        return result
    except FileNotFoundError:
        console.print("[yellow]⚠️ twine not found. Install with: pip install twine[/yellow]")
        
        # Fallback to basic check
        dist_dir = PROJECT_ROOT / "dist"
        if not dist_dir.exists() or not list(dist_dir.glob("*")):
            console.print("[red]❌ No distribution files found. Run 'dev-cli build package' first[/red]")
            return 1
        
        console.print("[green]✅ Distribution files exist[/green]")
        return 0


@build_app.command()
def clean():
    """Clean build artifacts."""
    console.print("[bold blue]🧹 Cleaning build artifacts...[/bold blue]")
    
    artifacts = get_build_artifacts()
    
    if not artifacts:
        console.print("[green]✅ No build artifacts to clean[/green]")
        return 0
    
    console.print(f"[blue]Found {len(artifacts)} build artifacts:[/blue]")
    for artifact in artifacts:
        console.print(f"  • {artifact}")
    
    removed = 0
    failed = 0
    
    for artifact in artifacts:
        if safe_remove_path(artifact):
            removed += 1
        else:
            failed += 1
    
    if removed > 0:
        console.print(f"[green]✅ Removed {removed} build artifacts[/green]")
    
    if failed > 0:
        console.print(f"[red]❌ Failed to remove {failed} artifacts[/red]")
        return 1
    
    return 0


@build_app.command()
def deps():
    """Show build dependencies and their status."""
    console.print("[bold blue]📋 Build dependencies:[/bold blue]")
    
    dependencies = [
        ("build", "Package building"),
        ("twine", "Package checking and uploading"),
        ("wheel", "Wheel format support"),
        ("setuptools", "Package setup tools"),
    ]
    
    from rich.table import Table
    
    table = Table(title="Build Dependencies")
    table.add_column("Package", style="cyan")
    table.add_column("Purpose", style="yellow")
    table.add_column("Status", style="green")
    
    for package, purpose in dependencies:
        try:
            __import__(package)
            status = "✅ Available"
        except ImportError:
            status = "❌ Missing"
        
        table.add_row(package, purpose, status)
    
    console.print(table)
    
    # Check if any are missing
    missing = []
    for package, _ in dependencies:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        console.print(f"\n[red]Missing dependencies: {', '.join(missing)}[/red]")
        console.print("[blue]Install with: pip install build twine[/blue]")
        return 1
    else:
        console.print("\n[green]✅ All build dependencies available[/green]")
        return 0


@build_app.command()
def info():
    """Show build and package information."""
    console.print("[bold blue]📋 Build Information:[/bold blue]")
    
    # Read version from pyproject.toml
    pyproject_file = PROJECT_ROOT / "pyproject.toml"
    version = "unknown"
    name = "unknown"
    
    if pyproject_file.exists():
        try:
            import tomllib
            with open(pyproject_file, "rb") as f:
                data = tomllib.load(f)
                version = data.get("project", {}).get("version", "unknown")
                name = data.get("project", {}).get("name", "unknown")
        except ImportError:
            # Fallback for Python < 3.11
            try:
                import tomli
                with open(pyproject_file, "rb") as f:
                    data = tomli.load(f)
                    version = data.get("project", {}).get("version", "unknown")
                    name = data.get("project", {}).get("name", "unknown")
            except ImportError:
                console.print("[yellow]⚠️ Cannot read pyproject.toml (tomllib/tomli not available)[/yellow]")
    
    from rich.table import Table
    
    table = Table(title="Package Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Name", name)
    table.add_row("Version", version)
    table.add_row("Project Root", str(PROJECT_ROOT))
    
    # Check for distribution files
    dist_dir = PROJECT_ROOT / "dist"
    if dist_dir.exists():
        dist_files = list(dist_dir.glob("*"))
        table.add_row("Distribution Files", str(len(dist_files)))
    else:
        table.add_row("Distribution Files", "0")
    
    console.print(table)
