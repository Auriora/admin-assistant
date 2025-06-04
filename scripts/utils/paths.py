"""Path management utilities."""
from pathlib import Path
from typing import List, Generator

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = PROJECT_ROOT / "src"
TESTS_PATH = PROJECT_ROOT / "tests"
SCRIPTS_PATH = PROJECT_ROOT / "scripts"
DOCS_PATH = PROJECT_ROOT / "docs"
BUILD_PATH = PROJECT_ROOT / "build"
DIST_PATH = PROJECT_ROOT / "dist"
HTMLCOV_PATH = PROJECT_ROOT / "htmlcov"
INSTANCE_PATH = PROJECT_ROOT / "instance"
LOGS_PATH = PROJECT_ROOT / "logs"


def get_build_artifacts() -> List[Path]:
    """Get list of build artifact paths."""
    artifacts = []
    
    # Build directories
    build_dirs = [BUILD_PATH, DIST_PATH]
    for build_dir in build_dirs:
        if build_dir.exists():
            artifacts.append(build_dir)
    
    # Egg info directories
    for egg_info in PROJECT_ROOT.glob("*.egg-info"):
        artifacts.append(egg_info)
    
    # Egg info in src
    for egg_info in SRC_PATH.glob("*.egg-info"):
        artifacts.append(egg_info)
    
    return artifacts


def get_test_artifacts() -> List[Path]:
    """Get list of test artifact paths."""
    artifacts = []
    
    # Coverage files and directories
    coverage_paths = [
        PROJECT_ROOT / ".coverage",
        PROJECT_ROOT / "coverage.xml",
        HTMLCOV_PATH,
    ]
    
    for path in coverage_paths:
        if path.exists():
            artifacts.append(path)
    
    # Pytest cache
    pytest_cache = PROJECT_ROOT / ".pytest_cache"
    if pytest_cache.exists():
        artifacts.append(pytest_cache)
    
    # Coverage files with patterns
    for coverage_file in PROJECT_ROOT.glob(".coverage.*"):
        artifacts.append(coverage_file)
    
    return artifacts


def get_python_cache() -> Generator[Path, None, None]:
    """Get Python cache files and directories."""
    # __pycache__ directories
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        yield pycache
    
    # .pyc files
    for pyc_file in PROJECT_ROOT.rglob("*.pyc"):
        yield pyc_file
    
    # .pyo files
    for pyo_file in PROJECT_ROOT.rglob("*.pyo"):
        yield pyo_file


def get_temp_files() -> List[Path]:
    """Get temporary files and directories."""
    temp_paths = []
    
    # Log files (but keep the logs directory)
    if LOGS_PATH.exists():
        for log_file in LOGS_PATH.glob("*.log"):
            temp_paths.append(log_file)
    
    # Temporary files
    temp_patterns = ["*.tmp", "*.temp", "*~", ".DS_Store"]
    for pattern in temp_patterns:
        for temp_file in PROJECT_ROOT.rglob(pattern):
            temp_paths.append(temp_file)
    
    return temp_paths


def get_node_artifacts() -> List[Path]:
    """Get Node.js artifacts (from web assets)."""
    artifacts = []
    
    # node_modules directories
    for node_modules in PROJECT_ROOT.rglob("node_modules"):
        artifacts.append(node_modules)
    
    # package-lock.json files
    for lock_file in PROJECT_ROOT.rglob("package-lock.json"):
        artifacts.append(lock_file)
    
    return artifacts


def ensure_directory(path: Path) -> Path:
    """Ensure directory exists, create if it doesn't."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_remove_path(path: Path) -> bool:
    """Safely remove a file or directory."""
    try:
        if path.is_file():
            path.unlink()
            return True
        elif path.is_dir():
            import shutil
            shutil.rmtree(path)
            return True
        return False
    except (OSError, PermissionError):
        return False
