"""Test-related commands."""
import subprocess
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from scripts.utils.environment import setup_test_environment, get_project_root

console = Console()
test_app = typer.Typer(help="Testing commands")

PROJECT_ROOT = get_project_root()


def run_command(cmd: List[str], description: str) -> int:
    """Run a command with progress indication."""
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
            console.print("\n[red]Test execution interrupted by user[/red]")
            return 130
        except Exception as e:
            console.print(f"\n[red]Error running tests: {e}[/red]")
            return 1


@test_app.command()
def unit(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    coverage: bool = typer.Option(False, "--coverage", "-c", help="Generate coverage report"),
):
    """Run unit tests."""
    setup_test_environment()
    
    cmd = ['python', '-m', 'pytest', 'tests/unit/', '-m', 'unit']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=src/core', '--cov=src/cli', '--cov-report=term-missing'])
    
    console.print("[bold blue]Running unit tests...[/bold blue]")
    return run_command(cmd, "Running unit tests")


@test_app.command()
def integration(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run integration tests."""
    setup_test_environment()
    
    cmd = ['python', '-m', 'pytest', 'tests/integration/', '-m', 'integration']
    
    if verbose:
        cmd.append('-v')
    
    console.print("[bold blue]Running integration tests...[/bold blue]")
    return run_command(cmd, "Running integration tests")


@test_app.command()
def all(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    coverage: bool = typer.Option(False, "--coverage", "-c", help="Generate coverage report"),
):
    """Run all tests."""
    setup_test_environment()
    
    cmd = ['python', '-m', 'pytest', 'tests/']
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=src/core', '--cov=src/cli', 
            '--cov-report=term-missing', '--cov-report=html'
        ])
    
    console.print("[bold blue]Running all tests...[/bold blue]")
    return run_command(cmd, "Running all tests")


@test_app.command()
def specific(
    test_path: str = typer.Argument(..., help="Specific test file or function to run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run a specific test file or test function."""
    setup_test_environment()
    
    cmd = ['python', '-m', 'pytest', test_path]
    
    if verbose:
        cmd.append('-v')
    
    console.print(f"[bold blue]Running specific test: {test_path}[/bold blue]")
    return run_command(cmd, f"Running {test_path}")


@test_app.command()
def marker(
    marker_name: str = typer.Argument(..., help="Test marker to run"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run tests with a specific marker."""
    setup_test_environment()
    
    cmd = ['python', '-m', 'pytest', '-m', marker_name]
    
    if verbose:
        cmd.append('-v')
    
    console.print(f"[bold blue]Running tests with marker: {marker_name}[/bold blue]")
    return run_command(cmd, f"Running tests with marker {marker_name}")


@test_app.command()
def archiving(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    coverage: bool = typer.Option(False, "--coverage", "-c", help="Generate coverage report"),
):
    """Run tests specifically for archiving functionality."""
    setup_test_environment()
    
    test_files = [
        'tests/unit/services/test_calendar_archive_service_enhanced.py',
        'tests/unit/orchestrators/test_calendar_archive_orchestrator_enhanced.py',
        'tests/integration/test_archiving_flow_integration.py',
        'tests/unit/repositories/test_archive_configuration_repository.py',
        'tests/unit/repositories/test_action_log_repository.py'
    ]
    
    # Filter to only existing files
    existing_files = [f for f in test_files if (PROJECT_ROOT / f).exists()]
    
    if not existing_files:
        console.print("[red]No archiving test files found[/red]")
        return 1
    
    cmd = ['python', '-m', 'pytest'] + existing_files
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend([
            '--cov=src/core.services.calendar_archive_service',
            '--cov=src/core.orchestrators.calendar_archive_orchestrator',
            '--cov-report=term-missing'
        ])
    
    console.print("[bold blue]Running archiving-specific tests...[/bold blue]")
    return run_command(cmd, "Running archiving tests")


@test_app.command()
def observability(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run tests that verify OpenTelemetry integration."""
    # Enable OpenTelemetry for these tests
    import os
    os.environ['ENABLE_OTEL_IN_TESTS'] = 'true'
    os.environ.pop('OTEL_SDK_DISABLED', None)
    
    setup_test_environment()
    
    cmd = ['python', '-m', 'pytest', '-k', 'otel or telemetry or tracing or metrics']
    
    if verbose:
        cmd.append('-v')
    
    console.print("[bold blue]Running observability tests...[/bold blue]")
    return run_command(cmd, "Running observability tests")


@test_app.command()
def coverage(
    fail_under: int = typer.Option(80, "--fail-under", help="Minimum coverage percentage"),
):
    """Generate and display test coverage report."""
    setup_test_environment()
    
    cmd = [
        'python', '-m', 'pytest', 
        '--cov=src/core', '--cov=src/cli',
        '--cov-report=html', '--cov-report=term-missing',
        f'--cov-fail-under={fail_under}', 'tests/'
    ]
    
    console.print("[bold blue]Generating coverage report...[/bold blue]")
    result = run_command(cmd, "Generating coverage report")
    
    if result == 0:
        console.print("\n[green]✅ Coverage report generated successfully![/green]")
        console.print("[blue]HTML report available at: htmlcov/index.html[/blue]")
    else:
        console.print(f"\n[red]❌ Coverage check failed - coverage below {fail_under}%[/red]")
    
    return result


@test_app.command()
def lint():
    """Run linting on test files."""
    try:
        # Check if flake8 is available
        subprocess.run(['flake8', '--version'], capture_output=True, check=True)
        
        cmd = ['flake8', 'tests/', '--max-line-length=120', '--ignore=E501,W503']
        console.print("[bold blue]Running linting on test files...[/bold blue]")
        return run_command(cmd, "Linting test files")
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[yellow]flake8 not available, skipping linting[/yellow]")
        return 0
