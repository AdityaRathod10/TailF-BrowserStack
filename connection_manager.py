import json
import asyncio
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections for real-time log streaming.
    Handles connection lifecycle and broadcasting messages to all connected clients.
    """
    
    def __init__(self):
        
        self.active_connections: List[WebSocket] = []
        
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """
        Accept a new WebSocket connection and add it to active connections.
        
        Args:
            websocket: The WebSocket connection
            client_info: Optional metadata about the client
        """
        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            
            
            if client_info:
                self.connection_info[websocket] = client_info
            
            logger.info(f"New connection established. Total connections: {len(self.active_connections)}")
            
        
            await self.send_personal_message({
                "type": "connection_status", 
                "status": "connected",
                "message": "Successfully connected to log stream"
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            raise
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from active connections.
        
        Args:
            websocket: The WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        if websocket in self.connection_info:
            del self.connection_info[websocket]
            
        logger.info(f"Connection disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: Dictionary message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            
            self.disconnect(websocket)
    
    async def broadcast_message(self, message: Dict[str, Any]):
        """
        Broadcast a message to all active WebSocket connections.
        
        Args:
            message: Dictionary message to broadcast
        """
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected_connections = []
        
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                
                disconnected_connections.append(connection)
        
        
        for connection in disconnected_connections:
            self.disconnect(connection)
        
        if disconnected_connections:
            logger.info(f"Cleaned up {len(disconnected_connections)} broken connections")
    
    async def broadcast_new_lines(self, lines: List[str]):
        """
        Broadcast new log lines to all connected clients.
        
        Args:
            lines: List of new log lines to broadcast
        """
        if not lines:
            return
            
        message = {
            "type": "new_lines",
            "lines": lines,
            "timestamp": asyncio.get_event_loop().time(),
            "count": len(lines)
        }
        
        await self.broadcast_message(message)
        logger.info(f"Broadcasted {len(lines)} new lines to {len(self.active_connections)} clients")
    
    async def send_initial_lines(self, lines: List[str], websocket: WebSocket):
        """
        Send initial log lines to a newly connected client.
        
        Args:
            lines: List of initial log lines
            websocket: Target WebSocket connection
        """
        message = {
            "type": "initial_lines",
            "lines": lines,
            "timestamp": asyncio.get_event_loop().time(),
            "count": len(lines)
        }
        
        await self.send_personal_message(message, websocket)
        logger.info(f"Sent {len(lines)} initial lines to new client")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get detailed connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "connection_info": {
                str(id(ws)): info for ws, info in self.connection_info.items()
            }
        }


manager = ConnectionManager()