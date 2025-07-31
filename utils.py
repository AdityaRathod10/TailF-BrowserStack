import os
import asyncio
from typing import List, Tuple
from pathlib import Path
import chardet 

def detect_file_encoding(file_path: str) -> str:
    """Detect the encoding of a file."""
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read(min(10000, os.path.getsize(file_path)))
            if raw_data:
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8')
                
                if encoding and 'utf-16' in encoding.lower():
                    return 'utf-16'
                elif encoding and encoding.lower() in ['ascii', 'utf-8']:
                    return 'utf-8'
                else:
                    return encoding or 'utf-8'
    except:
        pass
    return 'utf-8'

def read_last_n_lines(file_path: str, n: int = 10) -> list[str]:
    """Efficiently read the last N lines from a potentially large file."""
    if not os.path.exists(file_path) or n <= 0:
        return []
    buffer = bytearray()
    chunk_size = 1024
    with open(file_path, 'rb') as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        pointer = file_size
        while pointer > 0 and buffer.count(b'\n') <= n:
            read_size = min(chunk_size, pointer)
            pointer -= read_size
            f.seek(pointer)
            buffer = f.read(read_size) + buffer
    
    lines = buffer.split(b'\n')
    
    result = [line.decode(errors='replace').rstrip('\r\n') for line in lines if line.strip()]
    return result[-n:]

def get_file_size(file_path: str) -> int:
    """Get the current size of a file."""
    try:
        return os.path.getsize(file_path)
    except (OSError, FileNotFoundError):
        return 0

def read_new_lines(file_path: str, last_position: int) -> Tuple[List[str], int]:
    """
    Read new lines from a file starting from a given position.
    
    Args:
        file_path: Path to the log file
        last_position: Last known file position
    
    Returns:
        Tuple of (new_lines_list, new_position)
    """
    if not os.path.exists(file_path):
        return [], last_position
    
    try:
        current_size = get_file_size(file_path)
        
        
        if current_size <= last_position:
            return [], last_position
        
        encoding = detect_file_encoding(file_path)
        new_lines = []
        
        with open(file_path, 'r', encoding=encoding, errors='replace') as file:
            file.seek(last_position)
            new_content = file.read(current_size - last_position)
            
            
            lines = new_content.split('\n')
            
            
            for line in lines:
                cleaned_line = line.rstrip('\r\n')
                if cleaned_line.strip():  
                    new_lines.append(cleaned_line)
        
        return new_lines, current_size
        
    except Exception as e:
        print(f"Error reading new lines from {file_path}: {e}")
        return [], last_position

async def ensure_log_file_exists(file_path: str) -> bool:
    """
    Ensure the log file exists, create if it doesn't.
    
    Args:
        file_path: Path to the log file
    
    Returns:
        True if file exists or was created successfully
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if not path.exists():
            path.touch()
            print(f"Created log file: {file_path}")
        
        return True
    except Exception as e:
        print(f"Error ensuring log file exists {file_path}: {e}")
        return False