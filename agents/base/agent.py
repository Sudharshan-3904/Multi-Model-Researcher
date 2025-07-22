"""
Base Agent Class - Foundation for all agents in the multi-agent system
"""

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
import httpx


class AgentStatus(Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class MessageType(Enum):
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    HEALTH_CHECK = "health_check"
    ERROR_REPORT = "error_report"


class Message(BaseModel):
    id: str
    sender: str
    recipient: str
    message_type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    priority: int = 1  # 1=low, 5=high


class TaskResult(BaseModel):
    task_id: str
    agent_id: str
    status: str
    result: Dict[str, Any]
    metadata: Dict[str, Any]
    execution_time: float
    timestamp: datetime


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system.
    Provides common functionality for communication, logging, and task management.
    """
    
    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        redis_url: str,
        config: Dict[str, Any] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config or {}
        self.status = AgentStatus.INITIALIZING
        
        # Redis connection for inter-agent communication
        self.redis_client = None
        self.redis_url = redis_url
        
        # Task management
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.task_queue = asyncio.Queue()
        
        # HTTP client for external APIs
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Logger setup
        self.logger = self._setup_logger()
        
        # Message handlers
        self.message_handlers: Dict[MessageType, Callable] = {
            MessageType.HEALTH_CHECK: self._handle_health_check,
            MessageType.STATUS_UPDATE: self._handle_status_update,
        }
        
        # FastAPI app
        self.app = FastAPI(title=f"{agent_type.title()} Agent")
        self._setup_routes()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup structured logging for the agent."""
        logger = logging.getLogger(f"{self.agent_type}.{self.agent_id}")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(filename)s:%(lineno)d - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def initialize(self):
        """Initialize the agent and its connections."""
        try:
            self.logger.info(f"Initializing {self.agent_type} agent {self.agent_id}")
            
            # Connect to Redis
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            
            # Subscribe to agent-specific channel
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe(f"agent:{self.agent_id}")
            
            # Start message listener
            asyncio.create_task(self._listen_for_messages())
            
            # Initialize agent-specific components
            await self._initialize_agent()
            
            self.status = AgentStatus.READY
            await self._broadcast_status_update()
            
            self.logger.info(f"{self.agent_type} agent {self.agent_id} initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize agent: {str(e)}")
            self.status = AgentStatus.ERROR
            raise
    
    @abstractmethod
    async def _initialize_agent(self):
        """Agent-specific initialization logic."""
        pass
    
    def _setup_routes(self):
        """Setup FastAPI routes common to all agents."""
        
        @self.app.get("/health")
        async def health_check():
            return {
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": self.status.value,
                "timestamp": datetime.now().isoformat(),
                "active_tasks": len(self.active_tasks)
            }
        
        @self.app.post("/tasks")
        async def create_task(task_data: Dict[str, Any]):
            try:
                task_id = str(uuid.uuid4())
                result = await self.execute_task(task_id, task_data)
                return {"task_id": task_id, "result": result}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/tasks/{task_id}")
        async def get_task_status(task_id: str):
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                return {
                    "task_id": task_id,
                    "status": "running" if not task.done() else "completed",
                    "done": task.done()
                }
            return {"error": "Task not found"}, 404
    
    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        priority: int = 1
    ) -> str:
        """Send a message to another agent."""
        message = Message(
            id=str(uuid.uuid4()),
            sender=self.agent_id,
            recipient=recipient,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            correlation_id=correlation_id,
            priority=priority
        )
        
        # Publish to recipient's channel
        channel = f"agent:{recipient}"
        await self.redis_client.publish(channel, message.json())
        
        # Store message for audit trail
        await self._store_message(message)
        
        self.logger.info(f"Sent message {message.id} to {recipient}")
        return message.id
    
    async def _listen_for_messages(self):
        """Listen for incoming messages from other agents."""
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        msg_data = json.loads(message['data'])
                        msg = Message(**msg_data)
                        await self._handle_message(msg)
                    except Exception as e:
                        self.logger.error(f"Failed to process message: {str(e)}")
        except Exception as e:
            self.logger.error(f"Message listener error: {str(e)}")
    
    async def _handle_message(self, message: Message):
        """Route incoming messages to appropriate handlers."""
        self.logger.info(f"Received message {message.id} from {message.sender}")
        
        # Store message for audit trail
        await self._store_message(message)
        
        # Route to handler
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                self.logger.error(f"Handler error for message {message.id}: {str(e)}")
                await self._send_error_response(message, str(e))
        else:
            self.logger.warning(f"No handler for message type {message.message_type}")
    
    async def _handle_health_check(self, message: Message):
        """Handle health check requests."""
        response_payload = {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "timestamp": datetime.now().isoformat(),
            "active_tasks": len(self.active_tasks)
        }
        
        await self.send_message(
            message.sender,
            MessageType.TASK_RESPONSE,
            response_payload,
            correlation_id=message.id
        )
    
    async def _handle_status_update(self, message: Message):
        """Handle status update notifications."""
        self.logger.info(f"Status update from {message.sender}: {message.payload}")
    
    async def _send_error_response(self, original_message: Message, error: str):
        """Send error response to message sender."""
        await self.send_message(
            original_message.sender,
            MessageType.ERROR_REPORT,
            {
                "original_message_id": original_message.id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            },
            correlation_id=original_message.id
        )
    
    async def _broadcast_status_update(self):
        """Broadcast status update to all agents."""
        await self.redis_client.publish(
            "agent:broadcast",
            json.dumps({
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "status": self.status.value,
                "timestamp": datetime.now().isoformat()
            })
        )
    
    async def _store_message(self, message: Message):
        """Store message in audit trail."""
        # This would typically go to a database
        # For now, we'll store in Redis with TTL
        key = f"audit:message:{message.id}"
        await self.redis_client.setex(
            key,
            3600 * 24 * 7,  # 7 days TTL
            message.json()
        )
    
    @abstractmethod
    async def execute_task(self, task_id: str, task_data: Dict[str, Any]) -> TaskResult:
        """Execute a task. Must be implemented by concrete agents."""
        pass
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """Register a custom message handler."""
        self.message_handlers[message_type] = handler
    
    async def shutdown(self):
        """Gracefully shutdown the agent."""
        self.logger.info(f"Shutting down {self.agent_type} agent {self.agent_id}")
        
        self.status = AgentStatus.MAINTENANCE
        await self._broadcast_status_update()
        
        # Cancel active tasks
        for task_id, task in self.active_tasks.items():
            task.cancel()
            self.logger.info(f"Cancelled task {task_id}")
        
        # Close connections
        if self.redis_client:
            await self.pubsub.unsubscribe()
            await self.redis_client.close()
        
        await self.http_client.aclose()
        
        self.logger.info(f"{self.agent_type} agent {self.agent_id} shutdown complete")


class AgentManager:
    """Utility class for managing multiple agents."""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("AgentManager")
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the manager."""
        self.agents[agent.agent_id] = agent
        self.logger.info(f"Registered agent {agent.agent_id}")
    
    async def initialize_all(self):
        """Initialize all registered agents."""
        tasks = [agent.initialize() for agent in self.agents.values()]
        await asyncio.gather(*tasks)
        self.logger.info("All agents initialized")
    
    async def shutdown_all(self):
        """Shutdown all registered agents."""
        tasks = [agent.shutdown() for agent in self.agents.values()]
        await asyncio.gather(*tasks)
        self.logger.info("All agents shutdown")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID."""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        return [
            {
                "agent_id": agent.agent_id,
                "agent_type": agent.agent_type,
                "status": agent.status.value
            }
            for agent in self.agents.values()
        ]