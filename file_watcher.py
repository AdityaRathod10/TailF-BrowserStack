import asyncio
import os
import logging
from typing import Optional, Callable, List
from utils import get_file_size, read_new_lines, ensure_log_file_exists

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileWatcher:
    """
    Asynchronous file watcher that monitors a log file for changes
    and triggers callbacks when new lines are detected.
    """
    
    def __init__(self, 
                 file_path: str, 
                 poll_interval: float = 0.1,
                 callback: Optional[Callable[[List[str]], None]] = None):
        """
        Initialize the file watcher.
        
        Args:
            file_path: Path to the file to monitor
            poll_interval: How often to check for changes (seconds)
            callback: Async function to call when new lines are detected
        """
        self.file_path = file_path
        self.poll_interval = poll_interval
        self.callback = callback
        
        
        self.last_size = 0
        self.last_position = 0
        
        
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start monitoring the file."""
        if self.is_running:
            logger.warning("File watcher is already running")
            return
        
        
        await ensure_log_file_exists(self.file_path)
        
        
        self.last_size = get_file_size(self.file_path)
        self.last_position = self.last_size
        
        self.is_running = True
        self.task = asyncio.create_task(self._watch_loop())
        
        logger.info(f"Started watching file: {self.file_path}")
        logger.info(f"Initial file size: {self.last_size} bytes")
    
    async def stop(self):
        """Stop monitoring the file."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.task and not self.task.cancelled():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("File watcher stopped")
    
    async def _watch_loop(self):
        """Main monitoring loop."""
        try:
            while self.is_running:
                await self._check_for_changes()
                await asyncio.sleep(self.poll_interval)
        except asyncio.CancelledError:
            logger.info("File watcher loop cancelled")
        except Exception as e:
            logger.error(f"Error in file watcher loop: {e}")
            self.is_running = False
    
    async def _check_for_changes(self):
        """Check if the file has new content."""
        try:
            current_size = get_file_size(self.file_path)
            if current_size < self.last_size:
                logger.info("File was truncated or recreated, resetting position")
                self.last_position = 0
                self.last_size = current_size
                return

            if current_size > self.last_size:
                
                new_lines, new_position = read_new_lines(self.file_path, self.last_position)
                if new_lines and self.callback:
                    await self.callback(new_lines)
                self.last_size = current_size
                self.last_position = new_position
                if new_lines:
                    logger.info(f"Detected {len(new_lines)} new lines")
        except Exception as e:
            logger.error(f"Error checking for file changes: {e}")
    
    def set_callback(self, callback: Callable[[List[str]], None]):
        """Set or update the callback function."""
        self.callback = callback
    
    def get_status(self) -> dict:
        """Get the current status of the file watcher."""
        return {
            "is_running": self.is_running,
            "file_path": self.file_path,
            "last_size": self.last_size,
            "last_position": self.last_position,
            "poll_interval": self.poll_interval,
            "file_exists": os.path.exists(self.file_path)
        }