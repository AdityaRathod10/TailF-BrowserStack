from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from utils import read_last_n_lines, get_file_size
from connection_manager import manager
from file_watcher import FileWatcher
import os
import asyncio
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Tail Web", version="1.0.0")


app.mount("/static", StaticFiles(directory="C:\\Users\\Asus\\Desktop\\BrowserStack\\frontend"), name="static")


LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "c:\\Users\\Asus\\Desktop\\BrowserStack\\logs\\sample.log")
INITIAL_LINES = int(os.getenv("INITIAL_LINES", "10"))
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "0.1"))


file_watcher: FileWatcher = None

@app.on_event("startup")
async def startup_event():
    """Initialize the file watcher when the app starts."""
    global file_watcher
    
    logger.info("Starting Tail Web Server...")
    
   
    file_watcher = FileWatcher(
        file_path=LOG_FILE_PATH,
        poll_interval=POLL_INTERVAL,
        callback=manager.broadcast_new_lines
    )
    
    await file_watcher.start()
    logger.info("File watcher started successfully")

@app.on_event("shutdown")  
async def shutdown_event():
    """Clean up when the app shuts down."""
    global file_watcher
    
    logger.info("Shutting down Tail Web Server...")
    
    if file_watcher:
        await file_watcher.stop()
    
    logger.info("File watcher stopped")

@app.get("/")
async def root():
    return {"message": "Tail Web Server is running!", "connections": manager.get_connection_count()}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/api/last-lines")
async def get_last_lines(lines: int = INITIAL_LINES):
    """Get the last N lines from the log file"""
    last_lines = read_last_n_lines(LOG_FILE_PATH, lines)
    return {
        "lines": last_lines,
        "count": len(last_lines),
        "file_size": get_file_size(LOG_FILE_PATH)
    }

@app.get("/api/file-info")
async def get_file_info():
    """Get information about the log file"""
    return {
        "file_path": LOG_FILE_PATH,
        "file_size": get_file_size(LOG_FILE_PATH),
        "exists": os.path.exists(LOG_FILE_PATH)
    }

@app.get("/api/status")
async def get_status():
    """Get server status including connections and file watcher info"""
    watcher_status = file_watcher.get_status() if file_watcher else {"is_running": False}
    
    return {
        "server": "running",
        "connections": manager.get_connection_stats(),
        "file_watcher": watcher_status,
        "config": {
            "log_file_path": LOG_FILE_PATH,
            "initial_lines": INITIAL_LINES,
            "poll_interval": POLL_INTERVAL
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, n: int = Query(INITIAL_LINES)):
    """WebSocket endpoint for real-time log streaming"""
    client_info = {
        "client_host": websocket.client.host if websocket.client else "unknown",
        "client_port": websocket.client.port if websocket.client else "unknown"
    }
    
    try:
        
        await manager.connect(websocket, client_info)
        
        
        initial_lines = read_last_n_lines(LOG_FILE_PATH, n)
        await manager.send_initial_lines(initial_lines, websocket)
        
       
        while True:
            try:
                
                data = await websocket.receive_text()
                
                
                if data == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)
                
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)