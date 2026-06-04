import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import mimetypes

from app.schemas import FileNode

router = APIRouter(prefix="/files", tags=["files"])

# Get the workspace base directory from environment variable
WORKSPACE_BASE_DIR = os.getenv("WORKSPACE_BASE_DIR", "/workspace")

def resolve_path(input_path: str) -> Path:
    """
    Resolve a path to an absolute path within the workspace.
    Raises ValueError if the path tries to escape the workspace.
    """
    workspace = Path(WORKSPACE_BASE_DIR).resolve()
    path = Path(input_path)
    
    # If input is absolute, use it directly, otherwise join with workspace
    if path.is_absolute():
        target = path.resolve()
    else:
        target = (workspace / path).resolve()
    
    # Security check: Ensure the target path is inside the workspace
    if not str(target).startswith(str(workspace)):
        raise ValueError("Access denied: Path outside workspace")
    
    return target

def build_file_tree(path: Path) -> FileNode:
    """
    Recursively build the file tree structure.
    """
    try:
        stat = path.stat()
        name = path.name
        is_dir = path.is_dir()
        
        children: Optional[List[FileNode]] = None
        if is_dir:
            try:
                # Sort directories first, then files
                items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                children = [build_file_tree(item) for item in items]
            except PermissionError:
                # If we can't read a directory, just list it as a leaf or handle gracefully
                pass

        return FileNode(
            name=name,
            path=str(path.relative_to(Path(WORKSPACE_BASE_DIR).resolve())), # Store relative path
            is_directory=is_dir,
            children=children,
            size=stat.st_size if not is_dir else None,
            modified_at=datetime.fromtimestamp(stat.st_mtime) if not is_dir else None
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Path not found")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

@router.get("/tree", response_model=FileNode)
async def get_file_tree(prjdir: str = Query(..., description="Project directory relative to workspace")):
    """
    Get file tree structure as nested FileNode objects.
    """
    try:
        target_path = resolve_path(prjdir)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directory not found")
            
        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is not a directory")
            
        return build_file_tree(target_path)
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/content")
async def get_file_content(path: str = Query(..., description="File path relative to workspace")):
    """
    Get file content as text.
    Returns error for non-text files or files over 1MB.
    """
    try:
        target_path = resolve_path(path)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        if target_path.is_dir():
            raise HTTPException(status_code=400, detail="Path is a directory, not a file")
            
        # Check file size (limit to 1MB)
        file_size = target_path.stat().st_size
        if file_size > 1 * 1024 * 1024: # 1MB
            raise HTTPException(status_code=413, detail="File too large to view (max 1MB)")
            
        # Guess mime type to check if it's text
        mime_type, _ = mimetypes.guess_type(str(target_path))
        # Basic heuristic: if it's not obviously text, try to decode. 
        # Some text files don't have mime types (like .py, .js without extension).
        # We will try to read as utf-8 and catch errors.
        try:
            content = target_path.read_text(encoding="utf-8")
            return {"content": content, "path": str(target_path.relative_to(Path(WORKSPACE_BASE_DIR).resolve()))}
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File is binary or not UTF-8 encoded")
            
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/download")
async def download_file(path: str = Query(..., description="File path relative to workspace")):
    """
    Download a file.
    """
    try:
        target_path = resolve_path(path)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
            
        if target_path.is_dir():
            raise HTTPException(status_code=400, detail="Cannot download a directory")
            
        return FileResponse(
            path=str(target_path),
            filename=target_path.name,
            media_type='application/octet-stream'
        )
        
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
