from pathlib import Path
from typing import Optional
from ..models import FileUtilsInput, FileUtilsOutput

def process_file(inputs: FileUtilsInput, project_dir: Optional[str] = None) -> FileUtilsOutput:
    """Process file operations"""
    operation = inputs.operation
    
    if operation == "validate":
        return _validate_file(inputs, project_dir)
    elif operation == "copy":
        return _copy_file(inputs, project_dir)
    elif operation == "move":
        return _move_file(inputs, project_dir)
    elif operation == "delete":
        return _delete_file(inputs, project_dir)
    elif operation == "write":
        return _write_file(inputs, project_dir)
    else:
        return FileUtilsOutput(
            success=False,
            message=f"Unknown operation: {operation}"
        )

def _validate_file(inputs: FileUtilsInput, project_dir: Optional[str] = None) -> FileUtilsOutput:
    """Validate file existence and type"""
    file_path = inputs.source_path
    if project_dir and not Path(file_path).is_absolute():
        file_path = Path(project_dir) / file_path
    
    path = Path(file_path)
    
    if not path.exists():
        return FileUtilsOutput(
            success=False,
            message=f"File not found: {file_path}"
        )
    
    if inputs.file_type and not str(path).endswith(inputs.file_type):
        return FileUtilsOutput(
            success=False,
            message=f"File type mismatch. Expected: {inputs.file_type}, Got: {path.suffix}"
        )
    
    return FileUtilsOutput(
        success=True,
        message=f"File validated successfully: {file_path}",
        file_path=str(path),
        file_size=path.stat().st_size
    )

def _copy_file(inputs: FileUtilsInput, project_dir: Optional[str] = None) -> FileUtilsOutput:
    """Copy file from source to target"""
    source_path = inputs.source_path
    target_path = inputs.target_path
    
    if project_dir:
        if not Path(source_path).is_absolute():
            source_path = Path(project_dir) / source_path
        if not Path(target_path).is_absolute():
            target_path = Path(project_dir) / target_path
    
    try:
        source = Path(source_path)
        target = Path(target_path)
        
        if not source.exists():
            return FileUtilsOutput(
                success=False,
                message=f"Source file not found: {source_path}"
            )
        
        # Create target directory if it doesn't exist
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        import shutil
        shutil.copy2(source, target)
        
        return FileUtilsOutput(
            success=True,
            message=f"File copied successfully: {source_path} -> {target_path}",
            file_path=str(target),
            file_size=target.stat().st_size
        )
    except Exception as e:
        return FileUtilsOutput(
            success=False,
            message=f"Failed to copy file: {str(e)}"
        )

def _move_file(inputs: FileUtilsInput, project_dir: Optional[str] = None) -> FileUtilsOutput:
    """Move file from source to target"""
    source_path = inputs.source_path
    target_path = inputs.target_path
    
    if project_dir:
        if not Path(source_path).is_absolute():
            source_path = Path(project_dir) / source_path
        if not Path(target_path).is_absolute():
            target_path = Path(project_dir) / target_path
    
    try:
        source = Path(source_path)
        target = Path(target_path)
        
        if not source.exists():
            return FileUtilsOutput(
                success=False,
                message=f"Source file not found: {source_path}"
            )
        
        # Create target directory if it doesn't exist
        target.parent.mkdir(parents=True, exist_ok=True)
        
        # Move file
        source.rename(target)
        
        return FileUtilsOutput(
            success=True,
            message=f"File moved successfully: {source_path} -> {target_path}",
            file_path=str(target),
            file_size=target.stat().st_size
        )
    except Exception as e:
        return FileUtilsOutput(
            success=False,
            message=f"Failed to move file: {str(e)}"
        )

def _delete_file(inputs: FileUtilsInput, project_dir: Optional[str] = None) -> FileUtilsOutput:
    """Delete file"""
    file_path = inputs.source_path
    
    if project_dir and not Path(file_path).is_absolute():
        file_path = Path(project_dir) / file_path
    
    try:
        path = Path(file_path)
        
        if not path.exists():
            return FileUtilsOutput(
                success=False,
                message=f"File not found: {file_path}"
            )
        
        # Delete file
        path.unlink()
        
        return FileUtilsOutput(
            success=True,
            message=f"File deleted successfully: {file_path}"
        )
    except Exception as e:
        return FileUtilsOutput(
            success=False,
            message=f"Failed to delete file: {str(e)}"
        )

def _write_file(inputs: FileUtilsInput, project_dir: Optional[str] = None) -> FileUtilsOutput:
    """Write content to file"""
    file_path = inputs.source_path
    content = inputs.content or ""
    
    if project_dir and not Path(file_path).is_absolute():
        file_path = Path(project_dir) / file_path
    
    try:
        path = Path(file_path)
        
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        with open(path, 'w') as f:
            f.write(content)
        
        return FileUtilsOutput(
            success=True,
            message=f"File written successfully: {file_path}",
            file_path=str(path),
            file_size=path.stat().st_size
        )
    except Exception as e:
        return FileUtilsOutput(
            success=False,
            message=f"Failed to write file: {str(e)}"
        ) 