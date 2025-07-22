"""
Data Collector Agent - Fetches data from various sources
"""

import asyncio
import json
import aiohttp
import aiofiles
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin, urlparse
from pathlib import Path

import feedparser
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl
from motor.motor_asyncio import AsyncIOMotorClient

from agents.base.agent import BaseAgent, MessageType, TaskResult, AgentStatus


class SourceType(str):
    WEB_SCRAPING = "web_scraping"
    API_ENDPOINT = "api_endpoint" 
    RSS_FEED = "rss_feed"
    ARXIV = "arxiv"
    FILE_UPLOAD = "file_upload"
    DATABASE = "database"


class DataSource(BaseModel):
    id: str
    name: str
    type: SourceType
    url: Optional[HttpUrl] = None
    config: Dict[str, Any] = {}
    headers: Dict[str, str] = {}
    rate_limit: int = 60  # requests per minute
    retry_config: Dict[str, Any] = {"max_retries": 3, "backoff_factor": 2}
    is_active: bool = True


class CollectionResult(BaseModel):
    source_id: str
    source_type: SourceType
    url: Optional[str] = None
    content: Union[str, Dict[str, Any]]
    metadata: Dict[str, Any]
    collected_at: datetime
    content_hash: str
    size_bytes: int
    format: str  # html, json, xml, pdf, etc.


class DataCollectorAgent(BaseAgent):
    """
    Data Collector Agent responsible for:
    - Fetching data from various web sources
    - Processing different data formats (HTML, JSON, XML, PDF)
    - Rate limiting and retry mechanisms
    - Content deduplication and storage
    - MCP (Model Context Protocol) integration
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, "data_collector", config["redis_url"], config)
        
        # Database connection
        self.db_client = None
        self.db = None
        
        # HTTP session for web requests
        self.session = None
        
        # Data sources registry
        self.data_sources: Dict[str, DataSource] = {}
        
        # Rate limiting
        self.rate_limiters: Dict[str, List[datetime]] = {}
        self.max_concurrent_requests = config.get("max_concurrent_requests", 5)
        self.request_semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Storage paths
        self.storage_path = Path(config.get("storage_path", "./data"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Content deduplication
        self.seen_content_hashes: set = set()
        
        # Setup message handlers
        self.register_message_handler(MessageType.TASK_REQUEST, self._handle_collection_task)
        
        self._setup_collector_routes()
    
    async def _initialize_agent(self):
        """Initialize data collector specific components."""
        # Connect to MongoDB
        self.db_client = AsyncIOMotorClient(self.config["mongodb_url"])
        self.db = self.db_client.agents_db
        
        # Create HTTP session with custom settings
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={
                'User-Agent': 'Multi-Agent-System-DataCollector/1.0'
            }
        )
        
        # Load existing data sources from database
        await self._load_data_sources()
        
        # Register capabilities with supervisor
        await self._register_with_supervisor()
        
        self.logger.info("Data collector agent initialization complete")
    
    def _setup_collector_routes(self):
        """Setup data collector specific FastAPI routes."""
        
        @self.app.post("/sources")
        async def add_data_source(source_data: Dict[str, Any]):
            """Add a new data source."""
            try:
                source = await self._add_data_source(source_data)
                return {"source_id": source.id, "status": "added"}
            except Exception as e:
                self.logger.error(f"Failed to add data source: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/sources")
        async def list_data_sources():
            """List all configured data sources."""
            return {
                "sources": [
                    {
                        "id": source.id,
                        "name": source.name,
                        "type": source.type,
                        "url": str(source.url) if source.url else None,
                        "is_active": source.is_active,
                        "last_collected": await self._get_last_collection_time(source.id)
                    }
                    for source in self.data_sources.values()
                ]
            }
        
        @self.app.post("/collect/{source_id}")
        async def collect_from_source(source_id: str):
            """Trigger collection from a specific source."""
            if source_id not in self.data_sources:
                raise HTTPException(status_code=404, detail="Data source not found")
            
            try:
                result = await self._collect_from_source(source_id)
                return {"collection_id": result.content_hash, "status": "completed"}
            except Exception as e:
                self.logger.error(f"Collection failed for source {source_id}: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/collect/url")
        async def collect_from_url(url_data: Dict[str, Any]):
            """Collect data from a single URL."""
            url = url_data.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="URL is required")
            
            try:
                result = await self._collect_from_url(url, url_data.get("options", {}))
                return {"content_hash": result.content_hash, "size": result.size_bytes}
            except Exception as e:
                self.logger.error(f"URL collection failed for {url}: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/collections/recent")
        async def get_recent_collections(limit: int = 50):
            """Get recent collection results."""
            collections = await self.db.collections.find({}).sort("collected_at", -1).limit(limit).to_list(None)
            return {"collections": collections}
    
    async def _add_data_source(self, source_data: Dict[str, Any]) -> DataSource:
        """Add a new data source to the registry."""
        source = DataSource(
            id=source_data.get("id", f"source_{len(self.data_sources)}"),
            name=source_data["name"],
            type=source_data["type"],
            url=source_data.get("url"),
            config=source_data.get("config", {}),
            headers=source_data.get("headers", {}),
            rate_limit=source_data.get("rate_limit", 60),
            retry_config=source_data.get("retry_config", {"max_retries": 3, "backoff_factor": 2})
        )
        
        self.data_sources[source.id] = source
        
        # Store in database
        await self.db.data_sources.insert_one(source.dict())
        
        self.logger.info(f"Added data source {source.id}: {source.name}")
        return source
    
    async def _load_data_sources(self):
        """Load existing data sources from database."""
        sources = await self.db.data_sources.find({"is_active": True}).to_list(None)
        for source_doc in sources:
            source = DataSource(**source_doc)
            self.data_sources[source.id] = source
        
        self.logger.info(f"Loaded {len(self.data_sources)} data sources")
    
    async def _register_with_supervisor(self):
        """Register this agent with the supervisor."""
        capabilities = [
            "web_scraping",
            "api_fetching", 
            "rss_collection",
            "arxiv_search",
            "file_processing",
            "content_parsing"
        ]
        
        try:
            await self.send_message(
                "supervisor",
                MessageType.TASK_REQUEST,
                {
                    "action": "register_agent",
                    "agent_id": self.agent_id,
                    "agent_type": self.agent_type,
                    "capabilities": capabilities,
                    "status": self.status.value
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to register with supervisor: {str(e)}")
    
    async def _handle_collection_task(self, message):
        """Handle data collection task requests."""
        payload = message.payload
        task_id = payload.get("task_id")
        task_type = payload.get("task_type")
        requirements = payload.get("requirements", {})
        
        try:
            if task_type == "web_scraping":
                result = await self