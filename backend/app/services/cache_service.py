import redis
import hashlib
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ResponseCacheService:
    def __init__(self):
        # Hooks directly into your existing operational redis container on port 6379
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST if hasattr(settings, 'REDIS_HOST') else 'localhost',
            port=6379,
            db=1,  # Using isolated DB index 1 to keep cache clear of celery queues
            decode_responses=True
        )
        self.default_ttl = 86400  # 24 Hours absolute cache expiration lifespans

    def _generate_cache_key(self, query_text: str, user_role: str) -> str:
        """
        🛡️ RBAC Secure Cache Key Rule:
        We hash the query string along with the user's role. This ensures an Engineer's 
        cached response never leaks privileged information from an HR executive's cache record!
        """
        normalized = query_text.strip().lower()
        composite_string = f"{user_role}:{normalized}"
        return f"rag_cache:{hashlib.sha256(composite_string.encode('utf-8')).hexdigest()}"

    def get_cached_response(self, query_text: str, user_role: str) -> Optional[str]:
        """Looks up existing identical query records inside the cache space."""
        try:
            cache_key = self._generate_cache_key(query_text, user_role)
            cached_val = self.redis_client.get(cache_key)
            if cached_val:
                logger.info(f"⚡ [Cache System] Hit! Intercepted query signature semantically matching.")
                return cached_val
            return None
        except Exception as e:
            logger.error(f"Redis cache extraction read error: {str(e)}")
            return None

    def set_cached_response(self, query_text: str, user_role: str, response_text: str):
        """Persists successful LLM outputs with an operational expiry window."""
        try:
            cache_key = self._generate_cache_key(query_text, user_role)
            self.redis_client.setex(
                name=cache_key,
                time=self.default_ttl,
                value=response_text
            )
            logger.info(f"💾 [Cache System] Stored new response key footprint into Redis storage tier.")
        except Exception as e:
            logger.error(f"Failed committing response to Redis cache: {str(e)}")

response_cache_service = ResponseCacheService()