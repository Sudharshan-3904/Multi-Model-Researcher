"""
Inter-agent communication utilities for the multi-agent system.
Handles message publishing, subscribing, and routing via Redis.
"""
import aioredis
import json

class CommunicationManager:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis = None

    async def connect(self):
        self.redis = await aioredis.create_redis_pool(self.redis_url)

    async def publish(self, channel: str, message: dict):
        # Serialize message to JSON and publish
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str):
        # Subscribe to a channel and return the channel object
        channels = await self.redis.subscribe(channel)
        return channels[0]

    async def close(self):
        self.redis.close()
        await self.redis.wait_closed()
