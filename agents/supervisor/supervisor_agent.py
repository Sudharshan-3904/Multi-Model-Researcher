"""
Supervisor Agent - Orchestrates tasks across the multi-agent system
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from enum import Enum

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorClient

from agents.base.agent import BaseAgent, MessageType, TaskResult, AgentStatus


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 3
    HIGH = 5
    CRITICAL = 10


class Task(BaseModel):
    id: str
    type: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    assigned_agent: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requirements: Dict[str, Any] = {}
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class WorkflowStep(BaseModel):
    id: str
    agent_type: str
    task_type: str
    depends_on: List[str] = []  # IDs of prerequisite steps
    parameters: Dict[str, Any] = {}
    timeout: int = 300  # seconds


class Workflow(BaseModel):
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: datetime
    status: TaskStatus = TaskStatus.PENDING


class SupervisorAgent(BaseAgent):
    """
    Supervisor Agent responsible for:
    - Task orchestration and workflow management
    - Agent health monitoring and load balancing
    - Quality control and result validation
    - System-wide coordination and decision making
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, "supervisor", config["redis_url"], config)
        
        # Database connection
        self.db_client = None
        self.db = None
        
        # Agent registry and health tracking
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_capabilities: Dict[str, Set[str]] = {}
        self.agent_load: Dict[str, int] = {}
        
        # Task and workflow management
        self.active_tasks: Dict[str, Task] = {}
        self.active_workflows: Dict[str, Workflow] = {}
        self.task_assignment_strategy = config.get("task_assignment", "round_robin")
        
        # Quality control
        self.quality_thresholds = config.get("quality_thresholds", {
            "confidence_score": 0.8,
            "completion_time": 300,
            "retry_limit": 3
        })
        
        # Setup additional message handlers
        self.register_message_handler(MessageType.TASK_REQUEST, self._handle_task_request)
        self.register_message_handler(MessageType.TASK_RESPONSE, self._handle_task_response)
        
        self._setup_supervisor_routes()
    
    async def _initialize_agent(self):
        """Initialize supervisor-specific components."""
        # Connect to MongoDB
        self.db_client = AsyncIOMotorClient(self.config["mongodb_url"])
        self.db = self.db_client.agents_db
        
        # Create indexes
        await self._create_indexes()
        
        # Start periodic health checks
        asyncio.create_task(self._health_check_loop())
        
        # Start workflow processor
        asyncio.create_task(self._workflow_processor())
        
        self.logger.info("Supervisor agent initialization complete")
    
    def _setup_supervisor_routes(self):
        """Setup supervisor-specific FastAPI routes."""
        
        @self.app.post("/workflows")
        async def create_workflow(workflow_data: Dict[str, Any]):
            """Create a new workflow."""
            try:
                workflow = await self._create_workflow(workflow_data)
                return {"workflow_id": workflow.id, "status": "created"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/workflows/{workflow_id}")
        async def get_workflow_status(workflow_id: str):
            """Get workflow status and progress."""
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                # Check database
                workflow_doc = await self.db.workflows.find_one({"id": workflow_id})
                if not workflow_doc:
                    raise HTTPException(status_code=404, detail="Workflow not found")
                workflow = Workflow(**workflow_doc)
            
            return {
                "workflow_id": workflow.id,
                "status": workflow.status.value,
                "steps": len(workflow.steps),
                "completed_steps": sum(1 for step in workflow.steps if step.id in self.active_tasks and 
                                     self.active_tasks[step.id].status == TaskStatus.COMPLETED)
            }
        
        @self.app.post("/tasks/single")
        async def create_single_task(task_data: Dict[str, Any]):
            """Create a single task without workflow."""
            try:
                task = await self._create_task(task_data)
                return {"task_id": task.id, "status": "created"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/agents")
        async def list_agents():
            """List all registered agents and their status."""
            return {
                "agents": [
                    {
                        "agent_id": agent_id,
                        "agent_type": info.get("type"),
                        "status": info.get("status"),
                        "last_seen": info.get("last_seen"),
                        "active_tasks": self.agent_load.get(agent_id, 0),
                        "capabilities": list(self.agent_capabilities.get(agent_id, set()))
                    }
                    for agent_id, info in self.registered_agents.items()
                ]
            }
        
        @self.app.post("/agents/{agent_id}/register")
        async def register_agent(agent_id: str, agent_info: Dict[str, Any]):
            """Register a new agent with the supervisor."""
            await self._register_agent(agent_id, agent_info)
            return {"status": "registered"}
        
        @self.app.get("/dashboard/stats")
        async def get_dashboard_stats():
            """Get system-wide statistics for dashboard."""
            total_tasks = await self.db.tasks.count_documents({})
            completed_tasks = await self.db.tasks.count_documents({"status": "completed"})
            failed_tasks = await self.db.tasks.count_documents({"status": "failed"})
            
            return {
                "total_agents": len(self.registered_agents),
                "active_agents": len([a for a in self.registered_agents.values() 
                                    if a.get("status") == "ready"]),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "active_workflows": len(self.active_workflows),
                "system_health": await self._calculate_system_health()
            }
    
    async def _create_workflow(self, workflow_data: Dict[str, Any]) -> Workflow:
        """Create a new workflow from specification."""
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=workflow_data["name"],
            description=workflow_data.get("description", ""),
            steps=[WorkflowStep(**step) for step in workflow_data["steps"]],
            created_at=datetime.now()
        )
        
        # Store workflow in database
        await self.db.workflows.insert_one(workflow.dict())
        
        # Add to active workflows
        self.active_workflows[workflow.id] = workflow
        
        # Start workflow execution
        asyncio.create_task(self._execute_workflow(workflow.id))
        
        self.logger.info(f"Created workflow {workflow.id}: {workflow.name}")
        return workflow
    
    async def _create_task(self, task_data: Dict[str, Any]) -> Task:
        """Create a single task."""
        task = Task(
            id=str(uuid.uuid4()),
            type=task_data["type"],
            description=task_data.get("description", ""),
            priority=TaskPriority(task_data.get("priority", 1)),
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            requirements=task_data.get("requirements", {}),
            max_retries=task_data.get("max_retries", 3)
        )
        
        # Store task in database
        await self.db.tasks.insert_one(task.dict())
        
        # Add to active tasks
        self.active_tasks[task.id] = task
        
        # Assign and execute task
        await self._assign_and_execute_task(task.id)
        
        return task
    
    async def _execute_workflow(self, workflow_id: str):
        """Execute a workflow by processing its steps in dependency order."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            self.logger.error(f"Workflow {workflow_id} not found")
            return
        
        self.logger.info(f"Starting workflow execution: {workflow.name}")
        workflow.status = TaskStatus.IN_PROGRESS
        
        # Build dependency graph
        completed_steps = set()
        step_tasks = {}
        
        try:
            while len(completed_steps) < len(workflow.steps):
                # Find steps ready for execution
                ready_steps = [
                    step for step in workflow.steps 
                    if step.id not in completed_steps and step.id not in step_tasks
                    and all(dep in completed_steps for dep in step.depends_on)
                ]
                
                if not ready_steps and len(completed_steps) < len(workflow.steps):
                    # Check if we're stuck (circular dependency or failed step)
                    if step_tasks:
                        # Wait for current tasks to complete
                        await asyncio.sleep(1)
                        continue
                    else:
                        # No ready steps and no running tasks = circular dependency
                        raise Exception("Circular dependency detected in workflow")
                
                # Execute ready steps
                for step in ready_steps:
                    task_data = {
                        "type": step.task_type,
                        "description": f"Workflow {workflow.name} - Step {step.id}",
                        "requirements": step.parameters,
                        "workflow_id": workflow_id,
                        "step_id": step.id
                    }
                    
                    task = await self._create_task(task_data)
                    step_tasks[step.id] = task.id
                
                # Wait for some tasks to complete
                while step_tasks:
                    for step_id, task_id in list(step_tasks.items()):
                        task = self.active_tasks.get(task_id)
                        if task and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                            if task.status == TaskStatus.COMPLETED:
                                completed_steps.add(step_id)
                            else:
                                # Handle failed step
                                self.logger.error(f"Step {step_id} failed: {task.error_message}")
                                workflow.status = TaskStatus.FAILED
                                return
                            
                            del step_tasks[step_id]
                    
                    if step_tasks:
                        await asyncio.sleep(1)
            
            # All steps completed successfully
            workflow.status = TaskStatus.COMPLETED
            self.logger.info(f"Workflow {workflow.name} completed successfully")
            
        except Exception as e:
            workflow.status = TaskStatus.FAILED
            self.logger.error(f"Workflow {workflow.name} failed: {str(e)}")
        
        finally:
            # Update workflow in database
            await self.db.workflows.update_one(
                {"id": workflow_id},
                {"$set": {"status": workflow.status.value}}
            )
    
    async def _assign_and_execute_task(self, task_id: str):
        """Assign a task to the best available agent and execute it."""
        task = self.active_tasks.get(task_id)
        if not task:
            self.logger.error(f"Task {task_id} not found")
            return
        
        # Find suitable agent
        agent_id = await self._select_agent_for_task(task)
        if not agent_id:
            self.logger.error(f"No suitable agent found for task {task_id}")
            task.status = TaskStatus.FAILED
            task.error_message = "No suitable agent available"
            return
        
        # Assign task
        task.assigned_agent = agent_id
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        task.updated_at = datetime.now()
        
        # Update agent load
        self.agent_load[agent_id] = self.agent_load.get(agent_id, 0) + 1
        
        # Send task to agent
        message_id = await self.send_message(
            agent_id,
            MessageType.TASK_REQUEST,
            {
                "task_id": task_id,
                "task_type": task.type,
                "requirements": task.requirements,
                "priority": task.priority.value
            },
            priority=task.priority.value
        )
        
        self.logger.info(f"Assigned task {task_id} to agent {agent_id}")
        
        # Set timeout for task completion
        asyncio.create_task(self._monitor_task_timeout(task_id, message_id))
    
    async def _select_agent_for_task(self, task: Task) -> Optional[str]:
        """Select the best agent for a given task based on various criteria."""
        suitable_agents = []
        
        # Find agents capable of handling this task type
        for agent_id, capabilities in self.agent_capabilities.items():
            if task.type in capabilities:
                agent_info = self.registered_agents.get(agent_id)
                if agent_info and agent_info.get("status") == "ready":
                    suitable_agents.append(agent_id)
        
        if not suitable_agents:
            return None
        
        # Apply selection strategy
        if self.task_assignment_strategy == "round_robin":
            return min(suitable_agents, key=lambda x: self.agent_load.get(x, 0))
        elif self.task_assignment_strategy == "random":
            import random
            return random.choice(suitable_agents)
        elif self.task_assignment_strategy == "load_balanced":
            return min(suitable_agents, key=lambda x: self.agent_load.get(x, 0))
        else:
            return suitable_agents[0]
    
    async def _handle_task_request(self, message):
        """Handle task requests from other agents or external sources."""
        payload = message.payload
        task_data = {
            "type": payload.get("task_type"),
            "description": payload.get("description", ""),
            "requirements": payload.get("requirements", {}),
            "priority": payload.get("priority", 1)
        }
        
        task = await self._create_task(task_data)
        
        # Send response
        await self.send_message(
            message.sender,
            MessageType.TASK_RESPONSE,
            {
                "task_id": task.id,
                "status": "accepted"
            },
            correlation_id=message.id
        )
    
    async def _handle_task_response(self, message):
        """Handle task completion responses from agents."""
        payload = message.payload
        task_id = payload.get("task_id")
        
        if not task_id or task_id not in self.active_tasks:
            self.logger.error(f"Unknown task ID in response: {task_id}")
            return
        
        task = self.active_tasks[task_id]
        
        # Update task status
        if payload.get("status") == "completed":
            task.status = TaskStatus.COMPLETED
            task.result = payload.get("result", {})
            task.completed_at = datetime.now()
            
            # Validate result quality
            if await self._validate_task_result(task):
                self.logger.info(f"Task {task_id} completed successfully")
            else:
                self.logger.warning(f"Task {task_id} completed but failed quality validation")
                # Could trigger retry or alternative processing
        
        elif payload.get("status") == "failed":
            task.status = TaskStatus.FAILED
            task.error_message = payload.get("error", "Unknown error")
            
            # Consider retry
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                await self._assign_and_execute_task(task_id)
                return
        
        # Update agent load
        if task.assigned_agent:
            current_load = self.agent_load.get(task.assigned_agent, 0)
            self.agent_load[task.assigned_agent] = max(0, current_load - 1)
        
        # Update database
        task.updated_at = datetime.now()
        await self.db.tasks.update_one(
            {"id": task_id},
            {"$set": task.dict()}
        )
    
    async def _validate_task_result(self, task: Task) -> bool:
        """Validate task result quality against configured thresholds."""
        if not task.result:
            return False
        
        # Check confidence score if provided
        confidence = task.result.get("confidence_score")
        if confidence and confidence < self.quality_thresholds["confidence_score"]:
            return False
        
        # Check completion time
        if task.started_at and task.completed_at:
            execution_time = (task.completed_at - task.started_at).total_seconds()
            if execution_time > self.quality_thresholds["completion_time"]:
                self.logger.warning(f"Task {task.id} took {execution_time}s (threshold: {self.quality_thresholds['completion_time']}s)")
        
        # Additional quality checks can be added here
        return True
    
    async def _monitor_task_timeout(self, task_id: str, message_id: str):
        """Monitor task for timeout and handle accordingly."""
        timeout = self.config.get("task_timeout", 300)  # 5 minutes default
        await asyncio.sleep(timeout)
        
        task = self.active_tasks.get(task_id)
        if task and task.status == TaskStatus.IN_PROGRESS:
            self.logger.warning(f"Task {task_id} timed out")
            task.status = TaskStatus.FAILED
            task.error_message = f"Task timed out after {timeout} seconds"
            
            # Update agent load
            if task.assigned_agent:
                current_load = self.agent_load.get(task.assigned_agent, 0)
                self.agent_load[task.assigned_agent] = max(0, current_load - 1)
    
    async def _register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """Register a new agent with the supervisor."""
        self.registered_agents[agent_id] = {
            "type": agent_info.get("type"),
            "status": agent_info.get("status", "ready"),
            "capabilities": agent_info.get("capabilities", []),
            "last_seen": datetime.now(),
            "metadata": agent_info.get("metadata", {})
        }
        
        # Update capabilities mapping
        capabilities = set(agent_info.get("capabilities", []))
        self.agent_capabilities[agent_id] = capabilities
        self.agent_load[agent_id] = 0
        
        self.logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")
    
    async def _health_check_loop(self):
        """Periodically check health of all registered agents."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                for agent_id in list(self.registered_agents.keys()):
                    # Send health check
                    await self.send_message(
                        agent_id,
                        MessageType.HEALTH_CHECK,
                        {"timestamp": datetime.now().isoformat()}
                    )
                
            except Exception as e:
                self.logger.error(f"Health check loop error: {str(e)}")
    
    async def _workflow_processor(self):
        """Background task to process workflow queue."""
        while True:
            try:
                await asyncio.sleep(5)  # Process every 5 seconds
                
                # Clean up completed workflows
                completed_workflows = [
                    wf_id for wf_id, wf in self.active_workflows.items()
                    if wf.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                ]
                
                for wf_id in completed_workflows:
                    del self.active_workflows[wf_id]
                    self.logger.info(f"Cleaned up completed workflow {wf_id}")
                
            except Exception as e:
                self.logger.error(f"Workflow processor error: {str(e)}")
    
    async def _calculate_system_health(self) -> float:
        """Calculate overall system health score."""
        if not self.registered_agents:
            return 0.0
        
        healthy_agents = sum(1 for agent in self.registered_agents.values() 
                           if agent.get("status") == "ready")
        
        health_score = healthy_agents / len(self.registered_agents)
        
        # Factor in recent task success rate
        recent_tasks = await self.db.tasks.find(
            {"created_at": {"$gte": datetime.now() - timedelta(hours=1)}}
        ).to_list(None)
        
        if recent_tasks:
            successful_tasks = sum(1 for task in recent_tasks 
                                 if task.get("status") == "completed")
            task_success_rate = successful_tasks / len(recent_tasks)
            health_score = (health_score + task_success_rate) / 2
        
        return round(health_score, 2)
    
    async def _create_indexes(self):
        """Create database indexes for performance."""
        # Task indexes
        await self.db.tasks.create_index("id")
        await self.db.tasks.create_index("status")
        await self.db.tasks.create_index("created_at")
        await self.db.tasks.create_index("assigned_agent")
        
        # Workflow indexes
        await self.db.workflows.create_index("id")
        await self.db.workflows.create_index("status")
        await self.db.workflows.create_index("created_at")
        
        # Audit log indexes
        await self.db.audit_logs.create_index("timestamp")
        await self.db.audit_logs.create_index("agent_id")
        await self.db.audit_logs.create_index("message_id")
    
    async def execute_task(self, task_id: str, task_data: Dict[str, Any]) -> TaskResult:
        """Execute a task (supervisor delegates to other agents)."""
        # Supervisor doesn't execute tasks directly, it orchestrates
        task = await self._create_task(task_data)
        
        # Wait for completion (with timeout)
        timeout = task_data.get("timeout", 300)
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < timeout:
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
            await asyncio.sleep(1)
        
        return TaskResult(
            task_id=task.id,
            agent_id=self.agent_id,
            status=task.status.value,
            result=task.result or {},
            metadata={
                "assigned_agent": task.assigned_agent,
                "retry_count": task.retry_count,
                "execution_time": (task.completed_at - task.started_at).total_seconds() if task.completed_at and task.started_at else 0
            },
            execution_time=(datetime.now() - start_time).total_seconds(),
            timestamp=datetime.now()
        )