"""Environment setup and validation utilities."""
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
VENV_PATH = PROJECT_ROOT / ".venv"
SRC_PATH = PROJECT_ROOT / "src"
TESTS_PATH = PROJECT_ROOT / "tests"
SCRIPTS_PATH = PROJECT_ROOT / "scripts"


def get_project_root() -> Path:
    """Get the project root directory."""
    return PROJECT_ROOT


def setup_test_environment() -> Dict[str, str]:
    """Setup test environment variables."""
    env_vars = {
        'APP_ENV': 'testing',
        'DATABASE_URL': 'sqlite:///:memory:',
        'CORE_DATABASE_URL': 'sqlite:///:memory:',
        'LOG_LEVEL': 'INFO',
    }
    
    # Disable OpenTelemetry for tests unless explicitly enabled
    if 'ENABLE_OTEL_IN_TESTS' not in os.environ:
        env_vars['OTEL_SDK_DISABLED'] = 'true'
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    # Create instance directory for any file-based operations
    instance_dir = PROJECT_ROOT / 'instance'
    instance_dir.mkdir(exist_ok=True)
    
    return env_vars


def check_virtual_environment() -> bool:
    """Check if virtual environment is active."""
    return hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )


def check_dependencies() -> bool:
    """Check if required dependencies are installed."""
    try:
        import pytest
        import typer
        import rich
        return True
    except ImportError:
        return False


def get_python_info() -> Dict[str, Any]:
    """Get Python environment information."""
    return {
        'version': sys.version,
        'executable': sys.executable,
        'virtual_env': check_virtual_environment(),
        'venv_path': VENV_PATH if VENV_PATH.exists() else None,
    }


def get_git_info() -> Dict[str, Any]:
    """Get Git repository information."""
    try:
        branch = subprocess.check_output(
            ['git', 'branch', '--show-current'], 
            cwd=PROJECT_ROOT,
            text=True
        ).strip()
        
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=PROJECT_ROOT,
            text=True
        ).strip()
        
        status = subprocess.check_output(
            ['git', 'status', '--porcelain'],
            cwd=PROJECT_ROOT,
            text=True
        ).strip()
        
        return {
            'branch': branch,
            'commit': commit,
            'clean': len(status) == 0,
            'status': status
        }
    except subprocess.CalledProcessError:
        return {'error': 'Not a git repository or git not available'}


def show_environment_info():
    """Display comprehensive environment information."""
    console.print(Panel.fit("🔧 Development Environment Information", style="bold blue"))
    
    # Python information
    python_info = get_python_info()
    python_table = Table(title="Python Environment")
    python_table.add_column("Property", style="cyan")
    python_table.add_column("Value", style="green")
    
    python_table.add_row("Version", python_info['version'].split()[0])
    python_table.add_row("Executable", str(python_info['executable']))
    python_table.add_row("Virtual Environment", "✅ Active" if python_info['virtual_env'] else "❌ Not Active")
    if python_info['venv_path']:
        python_table.add_row("Venv Path", str(python_info['venv_path']))
    
    console.print(python_table)
    console.print()
    
    # Git information
    git_info = get_git_info()
    if 'error' not in git_info:
        git_table = Table(title="Git Repository")
        git_table.add_column("Property", style="cyan")
        git_table.add_column("Value", style="green")
        
        git_table.add_row("Branch", git_info['branch'])
        git_table.add_row("Commit", git_info['commit'])
        git_table.add_row("Status", "✅ Clean" if git_info['clean'] else "⚠️ Modified")
        
        console.print(git_table)
    else:
        console.print(f"[red]Git: {git_info['error']}[/red]")
    
    console.print()
    
    # Project paths
    paths_table = Table(title="Project Paths")
    paths_table.add_column("Path", style="cyan")
    paths_table.add_column("Exists", style="green")
    paths_table.add_column("Location", style="yellow")
    
    paths_to_check = [
        ("Project Root", PROJECT_ROOT),
        ("Source", SRC_PATH),
        ("Tests", TESTS_PATH),
        ("Scripts", SCRIPTS_PATH),
        ("Virtual Env", VENV_PATH),
    ]
    
    for name, path in paths_to_check:
        exists = "✅" if path.exists() else "❌"
        paths_table.add_row(name, exists, str(path))
    
    console.print(paths_table)
    
    # Dependencies check
    deps_ok = check_dependencies()
    console.print(f"\nDependencies: {'✅ Available' if deps_ok else '❌ Missing'}")
    
    if not deps_ok:
        console.print("[red]Run: pip install -e .[dev][/red]")
