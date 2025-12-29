"""
Evidence File Loader

Validates and loads user-uploaded case files.
"""

from pathlib import Path
from typing import List, Optional


def load_evidence_files(paths: Optional[List[str]]) -> List[Path]:
    """
    Validate and load evidence files from provided paths.
    
    Args:
        paths: List of file paths (relative or absolute)
        
    Returns:
        List of valid Path objects
    """
    if not paths:
        return []
    
    files = []
    for p in paths:
        path = Path(p)
        if path.exists() and path.is_file():
            files.append(path)
            print(f"✅ Loaded evidence: {path.name}")
        else:
            print(f"⚠️  Evidence file not found: {p}")
    
    return files
