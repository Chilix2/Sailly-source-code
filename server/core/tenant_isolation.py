"""
Tenant isolation helpers for Sailly multi-tenant FSM.

Provides utilities for:
- Composite key generation (tenant_id:object_type:id)
- Tenant_id extraction from conversation state
- Per-tenant rate limiting
- Redis namespace verification
"""

from __future__ import annotations

import logging
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


def make_composite_key(tenant_id: str, object_type: str, object_id: str) -> str:
    """
    Create a composite Redis key with tenant isolation.
    
    Args:
        tenant_id: Tenant identifier (doboo, pizzeria_napoli, etc.)
        object_type: Object type (conversation, order, reservation, etc.)
        object_id: Object identifier
    
    Returns:
        Composite key: {tenant_id}:{object_type}:{object_id}
    
    Example:
        make_composite_key("doboo", "conversation", "conv_abc123")
        → "doboo:conversation:conv_abc123"
    """
    if not tenant_id or not object_type or not object_id:
        raise ValueError(f"All key components required: tenant_id={tenant_id}, object_type={object_type}, object_id={object_id}")
    return f"{tenant_id}:{object_type}:{object_id}"


def extract_tenant_from_key(key: str) -> Optional[str]:
    """
    Extract tenant_id from composite key.
    
    Args:
        key: Composite Redis key
    
    Returns:
        Tenant ID or None if key format invalid
    
    Example:
        extract_tenant_from_key("doboo:conversation:conv_abc123")
        → "doboo"
    """
    if not key or ":" not in key:
        return None
    parts = key.split(":", 1)
    return parts[0]


def generate_call_id(tenant_id: str, user_id: Optional[str] = None) -> str:
    """
    Generate a unique call_id for 4-stack tracing.
    
    Args:
        tenant_id: Tenant identifier
        user_id: Optional user identifier (if known)
    
    Returns:
        Call ID: call_{uuid}_{tenant_id}_{user_id_prefix}
    
    Example:
        generate_call_id("doboo", "user_123")
        → "call_550e8400_doboo_user_"
    """
    unique_suffix = str(uuid.uuid4())[:8]
    user_prefix = user_id[:8] if user_id else "anon"
    return f"call_{unique_suffix}_{tenant_id}_{user_prefix}"


class TenantRateLimiter:
    """
    Per-tenant rate limiting to prevent noisy-neighbor effects.
    
    Tracks call counts and token usage per tenant.
    Raises exception if tenant exceeds quota.
    """
    
    def __init__(self, quota_per_hour: int = 1000, quota_tokens_per_day: int = 5000000):
        """
        Initialize rate limiter.
        
        Args:
            quota_per_hour: Max calls per hour per tenant (default: 1000)
            quota_tokens_per_day: Max tokens per day per tenant (default: 5M)
        """
        self.quota_per_hour = quota_per_hour
        self.quota_tokens_per_day = quota_tokens_per_day
        # In-memory tracking (in production, use Redis)
        self.tenant_calls: dict[str, list[float]] = {}
        self.tenant_tokens: dict[str, int] = {}
    
    def check_call_allowed(self, tenant_id: str) -> bool:
        """
        Check if tenant has calls remaining this hour.
        
        In production, replace with Redis-backed counter:
        ```python
        key = f"{tenant_id}:rate_limit:calls:{hour}"
        current = redis.incr(key)
        redis.expire(key, 3600)
        return current <= self.quota_per_hour
        ```
        
        Args:
            tenant_id: Tenant identifier
        
        Returns:
            True if call allowed, False if quota exceeded
        """
        # Placeholder for production Redis implementation
        logger.info(f"[TenantRateLimiter] call_allowed({tenant_id}): PLACEHOLDER (use Redis in production)")
        return True
    
    def check_token_budget(self, tenant_id: str, tokens_estimated: int) -> bool:
        """
        Check if tenant has token budget remaining today.
        
        Args:
            tenant_id: Tenant identifier
            tokens_estimated: Estimated tokens for this call
        
        Returns:
            True if budget available, False if would exceed quota
        """
        logger.info(f"[TenantRateLimiter] check_token_budget({tenant_id}, {tokens_estimated}): PLACEHOLDER (use Redis in production)")
        return True
    
    def record_call(self, tenant_id: str, tokens_used: int) -> None:
        """
        Record a call's token usage for this tenant.
        
        Args:
            tenant_id: Tenant identifier
            tokens_used: Actual tokens consumed
        """
        self.tenant_tokens.setdefault(tenant_id, 0)
        self.tenant_tokens[tenant_id] += tokens_used
        logger.debug(f"[TenantRateLimiter] Recorded {tokens_used} tokens for {tenant_id} (total: {self.tenant_tokens[tenant_id]})")


# Global rate limiter instance
_rate_limiter: Optional[TenantRateLimiter] = None


def get_rate_limiter() -> TenantRateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = TenantRateLimiter()
    return _rate_limiter


def verify_tenant_isolation(key: str, expected_tenant_id: str) -> bool:
    """
    Verify that a Redis key belongs to the expected tenant.
    
    Safety check to prevent cross-tenant data leaks.
    
    Args:
        key: Composite Redis key
        expected_tenant_id: Expected tenant_id from session
    
    Returns:
        True if key belongs to tenant, False otherwise
    """
    actual_tenant = extract_tenant_from_key(key)
    is_isolated = actual_tenant == expected_tenant_id
    if not is_isolated:
        logger.warning(f"[TenantIsolation] SECURITY: Key {key} belongs to {actual_tenant}, not {expected_tenant_id}")
    return is_isolated
