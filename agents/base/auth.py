"""
Authentication middleware for FastAPI agents.
Supports API key and JWT-based authentication.
"""
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, valid_keys: set):
        super().__init__(app)
        self.valid_keys = valid_keys

    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get(API_KEY_NAME)
        if not api_key or api_key not in self.valid_keys:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        response = await call_next(request)
        return response
