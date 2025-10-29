"""Storage backends for token persistence.

This module provides abstract base class and in-memory implementation
for storing token metadata.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime


class TokenStorage(ABC):
    """Abstract base class for token storage backends.

    Implement this interface to create custom storage backends
    for TokenManager.

    Methods:
        set: Store token data with key
        get: Retrieve token data by key
        delete: Remove token data by key
    """

    @abstractmethod
    def set(self, key: str, value: dict[str, Any]) -> None:
        """Store token data.

        Args:
            key: Token hash (unique identifier)
            value: Token metadata dict containing:
                - user_id: str
                - scopes: list[str]
                - type: 'access' | 'refresh'
                - expires_at: datetime
                - (optional) access_token_hash: str (for refresh tokens)
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve token data.

        Args:
            key: Token hash

        Returns:
            dict | None: Token metadata if found, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove token data.

        Args:
            key: Token hash
        """
        pass


class MemoryTokenStorage(TokenStorage):
    """In-memory token storage.

    Stores tokens in a Python dictionary. Data is lost when
    the process terminates. Suitable for single-instance deployments.

    For distributed deployments, implement custom TokenStorage
    backed by a database or external cache.

    Examples:
        >>> storage = MemoryTokenStorage()
        >>> storage.set('key123', {'user_id': 'user1', ...})
        >>> data = storage.get('key123')
        >>> storage.delete('key123')
    """

    def __init__(self) -> None:
        """Initialize empty storage."""
        self._store: dict[str, dict[str, Any]] = {}

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Store token data in memory.

        Args:
            key: Token hash
            value: Token metadata
        """
        # Store a copy to prevent external modifications
        stored_value = value.copy()

        # Convert datetime to ISO string for consistency
        if 'expires_at' in stored_value and isinstance(stored_value['expires_at'], datetime):
            stored_value['expires_at'] = stored_value['expires_at'].isoformat()

        self._store[key] = stored_value

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve token data from memory.

        Args:
            key: Token hash

        Returns:
            dict | None: Token metadata if found, None otherwise
        """
        value = self._store.get(key)

        if value is None:
            return None

        # Return a copy and convert ISO string back to datetime
        result = value.copy()
        if 'expires_at' in result and isinstance(result['expires_at'], str):
            result['expires_at'] = datetime.fromisoformat(result['expires_at'])

        return result

    def delete(self, key: str) -> None:
        """Remove token data from memory.

        Args:
            key: Token hash
        """
        self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all stored tokens (useful for testing)."""
        self._store.clear()
