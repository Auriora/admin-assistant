"""Test-related commands."""
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel

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
    """Run all core application tests (excludes utility tests)."""
    setup_test_environment()

    cmd = ['python', '-m', 'pytest', 'tests/', '-m', 'not utility and not dev']

    if verbose:
        cmd.append('-v')

    if coverage:
        cmd.extend([
            '--cov=src/core', '--cov=src/cli',
            '--cov-report=term-missing', '--cov-report=html'
        ])

    console.print("[bold blue]Running all core application tests...[/bold blue]")
    return run_command(cmd, "Running core application tests")


@test_app.command()
def all_inclusive(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    coverage: bool = typer.Option(False, "--coverage", "-c", help="Generate coverage report"),
):
    """Run all tests including utility and development tests."""
    setup_test_environment()

    cmd = ['python', '-m', 'pytest', 'tests/']

    if verbose:
        cmd.append('-v')

    if coverage:
        cmd.extend([
            '--cov=src/core', '--cov=src/cli',
            '--cov-report=term-missing', '--cov-report=html'
        ])

    console.print("[bold blue]Running all tests (including utilities)...[/bold blue]")
    return run_command(cmd, "Running all tests including utilities")


@test_app.command()
def utilities(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Run utility and development infrastructure tests only."""
    setup_test_environment()

    cmd = ['python', '-m', 'pytest', 'tests/', '-m', 'utility or dev']

    if verbose:
        cmd.append('-v')

    console.print("[bold blue]Running utility tests...[/bold blue]")
    return run_command(cmd, "Running utility tests")


@test_app.command()
def core(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    coverage: bool = typer.Option(False, "--coverage", "-c", help="Generate coverage report"),
):
    """Run core application tests only (alias for 'all' command)."""
    setup_test_environment()

    cmd = ['python', '-m', 'pytest', 'tests/', '-m', 'not utility and not dev']

    if verbose:
        cmd.append('-v')

    if coverage:
        cmd.extend([
            '--cov=src/core', '--cov=src/cli',
            '--cov-report=term-missing', '--cov-report=html'
        ])

    console.print("[bold blue]Running core application tests...[/bold blue]")
    return run_command(cmd, "Running core application tests")


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


@test_app.command()
def memory_profile(
    test_path: Optional[str] = typer.Argument(None, help="Specific test file or directory to profile"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    memray_enabled: bool = typer.Option(True, "--memray/--no-memray", help="Enable memray profiling"),
):
    """Run tests with memory profiling to diagnose SIGKILL (exit code 137) issues.

    This command monitors memory usage during test execution using psutil and optionally
    enables memray profiling for detailed memory allocation tracking.

    Examples:
        python scripts/dev_cli.py test memory-profile
        python scripts/dev_cli.py test memory-profile tests/unit/
        python scripts/dev_cli.py test memory-profile --verbose --no-memray
    """
    setup_test_environment()

    # Set environment variables for memory monitoring
    os.environ['MEMORY_PROFILING_ENABLED'] = 'true'
    os.environ['PYTEST_CURRENT_TEST_MEMORY_TRACKING'] = 'true'

    # Build pytest command using virtual environment python
    venv_python = PROJECT_ROOT / '.venv' / 'bin' / 'python'
    if venv_python.exists():
        cmd = [str(venv_python), '-m', 'pytest']
    else:
        cmd = ['python', '-m', 'pytest']

    if test_path:
        cmd.append(test_path)
    else:
        cmd.append('tests/')

    if verbose:
        cmd.append('-v')

    if memray_enabled:
        try:
            # Check if pytest-memray is available
            import pytest_memray
            cmd.extend(['--memray', '--most-allocations=5'])
            console.print("[blue]✅ Memray profiling enabled[/blue]")
        except ImportError:
            console.print("[yellow]⚠️  pytest-memray not available, install with: pip install pytest-memray[/yellow]")
            memray_enabled = False

    console.print(Panel.fit(
        "[bold blue]🔍 Memory Profiling Test Execution[/bold blue]\n"
        f"Target: {test_path or 'tests/'}\n"
        f"Memray: {'✅ Enabled' if memray_enabled else '❌ Disabled'}\n"
        f"Verbose: {'✅ Enabled' if verbose else '❌ Disabled'}",
        title="Memory Profile Configuration"
    ))

    # Start memory monitoring
    try:
        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        console.print(f"[dim]Initial memory usage: {initial_memory:.1f} MB[/dim]")

        # Track memory during execution
        max_memory = initial_memory
        memory_samples = []

        def monitor_memory():
            nonlocal max_memory
            try:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                max_memory = max(max_memory, current_memory)
                memory_samples.append(current_memory)
                return current_memory
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None

        # Run tests with memory monitoring
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running tests with memory profiling", total=None)

            start_time = time.time()

            try:
                # Start the subprocess
                proc = subprocess.Popen(cmd, cwd=PROJECT_ROOT)

                # Monitor memory usage
                while proc.poll() is None:
                    current_mem = monitor_memory()
                    if current_mem:
                        progress.update(task, description=f"Running tests (Memory: {current_mem:.1f} MB)")
                    time.sleep(0.5)  # Sample every 500ms

                # Get final result
                result = proc.wait()
                end_time = time.time()

                progress.update(task, completed=True)

            except KeyboardInterrupt:
                console.print("\n[red]Test execution interrupted by user[/red]")
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except:
                    proc.kill()
                return 130
            except Exception as e:
                console.print(f"\n[red]Error during test execution: {e}[/red]")
                return 1

        # Display memory usage summary
        execution_time = end_time - start_time
        final_memory = monitor_memory() or max_memory
        memory_increase = max_memory - initial_memory

        # Create memory usage table
        memory_table = Table(title="Memory Usage Summary")
        memory_table.add_column("Metric", style="cyan")
        memory_table.add_column("Value", style="green")

        memory_table.add_row("Initial Memory", f"{initial_memory:.1f} MB")
        memory_table.add_row("Peak Memory", f"{max_memory:.1f} MB")
        memory_table.add_row("Final Memory", f"{final_memory:.1f} MB")
        memory_table.add_row("Memory Increase", f"{memory_increase:.1f} MB")
        memory_table.add_row("Execution Time", f"{execution_time:.1f} seconds")
        memory_table.add_row("Exit Code", str(result))

        console.print()
        console.print(memory_table)

        # Memory analysis
        if result == 137:
            console.print(Panel(
                "[red]🚨 SIGKILL detected (exit code 137)![/red]\n"
                "This typically indicates the process was killed due to memory limits.\n"
                f"Peak memory usage: {max_memory:.1f} MB\n"
                "Consider:\n"
                "• Running tests in smaller batches\n"
                "• Using container limits to test memory constraints\n"
                "• Investigating memory-intensive test patterns",
                title="Memory Issue Detected",
                border_style="red"
            ))
        elif memory_increase > 500:  # More than 500MB increase
            console.print(Panel(
                f"[yellow]⚠️  High memory usage detected![/yellow]\n"
                f"Memory increased by {memory_increase:.1f} MB during execution.\n"
                "Consider investigating memory usage patterns.",
                title="High Memory Usage Warning",
                border_style="yellow"
            ))
        else:
            console.print("[green]✅ Memory usage appears normal[/green]")

        return result

    except ImportError:
        console.print("[red]❌ psutil not available. Install with: pip install psutil[/red]")
        console.print("[yellow]Falling back to basic test execution without memory monitoring[/yellow]")
        return run_command(cmd, "Running tests without memory monitoring")
