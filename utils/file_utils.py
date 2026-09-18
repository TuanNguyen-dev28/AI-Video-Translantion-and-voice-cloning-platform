"""
File utility functions.
"""
import shutil
from pathlib import Path
from typing import List


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_temp_files(directory: Path, pattern: str = "temp_*") -> int:
    """Clean temporary files matching pattern."""
    count = 0
    for f in directory.glob(pattern):
        try:
            f.unlink()
            count += 1
        except Exception:
            pass
    return count


def list_files_by_extension(directory: Path, extension: str) -> List[Path]:
    """List all files with given extension."""
    return sorted(directory.glob(f"*.{extension}"))


def get_file_size_mb(path: Path) -> float:
    """Get file size in MB."""
    if path.exists():
        return path.stat().st_size / (1024 * 1024)
    return 0.0


def copy_with_overwrite(src: Path, dst: Path) -> bool:
    """Copy file with overwrite."""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception:
        return False
