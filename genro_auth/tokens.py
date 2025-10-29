"""Token management for authentication and authorization.

This module provides the TokenManager class for generating, validating,
refreshing, and revoking access and refresh tokens.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
import secrets
import hashlib

from .storage import TokenStorage, MemoryTokenStorage


class TokenManager:
    """Manage access and refresh tokens with expiration and revocation.

    TokenManager handles the lifecycle of authentication tokens:
    - Generate token pairs (access + refresh)
    - Validate tokens and return user data
    - Refresh expired access tokens
    - Revoke tokens before expiration

    Tokens are opaque (random bytes) and stored hashed for security.

    Args:
        token_ttl: Access token lifetime in seconds (default: 3600 = 1 hour)
        refresh_ttl: Refresh token lifetime in seconds (default: 86400 = 24 hours)
        storage_backend: Storage implementation (default: MemoryTokenStorage)

    Examples:
        >>> manager = TokenManager(token_ttl=3600, refresh_ttl=86400)
        >>> tokens = manager.generate_token(user_id='user123', scopes=['read'])
        >>> user_data = manager.validate_token(tokens['access_token'])
        >>> print(user_data['user_id'])  # 'user123'
    """

    def __init__(
        self,
        token_ttl: int = 3600,
        refresh_ttl: int = 86400,
        storage_backend: Optional[TokenStorage] = None
    ):
        """Initialize TokenManager with configuration."""
        self.token_ttl = token_ttl
        self.refresh_ttl = refresh_ttl
        self.storage = storage_backend or MemoryTokenStorage()

    def generate_token(
        self,
        user_id: str,
        scopes: Optional[list[str]] = None
    ) -> dict[str, any]:
        """Generate a new access and refresh token pair.

        Creates cryptographically secure random tokens, hashes them,
        and stores metadata with expiration times.

        Args:
            user_id: Unique identifier for the user
            scopes: List of permission scopes (e.g., ['read', 'write'])

        Returns:
            dict: Token pair with metadata:
                {
                    'access_token': str,
                    'refresh_token': str,
                    'expires_in': int,
                    'token_type': 'Bearer'
                }

        Examples:
            >>> tokens = manager.generate_token(
            ...     user_id='user123',
            ...     scopes=['storage.read', 'storage.write']
            ... )
            >>> print(tokens['access_token'])  # Random secure token
        """
        # Generate secure random tokens
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        # Hash tokens for storage (security: don't store plaintext)
        access_hash = self._hash_token(access_token)
        refresh_hash = self._hash_token(refresh_token)

        # Calculate expiration times
        now = datetime.utcnow()
        access_expires = now + timedelta(seconds=self.token_ttl)
        refresh_expires = now + timedelta(seconds=self.refresh_ttl)

        # Store access token metadata
        self.storage.set(
            access_hash,
            {
                'user_id': user_id,
                'scopes': scopes or [],
                'type': 'access',
                'expires_at': access_expires
            }
        )

        # Store refresh token metadata (links to access token)
        self.storage.set(
            refresh_hash,
            {
                'user_id': user_id,
                'scopes': scopes or [],
                'access_token_hash': access_hash,
                'type': 'refresh',
                'expires_at': refresh_expires
            }
        )

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': self.token_ttl,
            'token_type': 'Bearer'
        }

    def validate_token(self, token: str) -> Optional[dict[str, any]]:
        """Validate an access token and return user data.

        Checks if token exists, hasn't expired, and is of type 'access'.
        Expired tokens are automatically removed from storage.

        Args:
            token: The access token to validate

        Returns:
            dict | None: User data if valid, None if invalid/expired:
                {
                    'user_id': str,
                    'scopes': list[str],
                    'type': 'access',
                    'expires_at': datetime
                }

        Examples:
            >>> user_data = manager.validate_token(access_token)
            >>> if user_data:
            ...     print(f"User: {user_data['user_id']}")
            ...     print(f"Scopes: {user_data['scopes']}")
            >>> else:
            ...     print("Invalid or expired token")
        """
        token_hash = self._hash_token(token)
        token_data = self.storage.get(token_hash)

        if not token_data:
            return None

        # Check if it's an access token (not refresh)
        if token_data.get('type') != 'access':
            return None

        # Check expiration
        expires_at = token_data.get('expires_at')
        if not expires_at or expires_at < datetime.utcnow():
            # Token expired, remove from storage
            self.storage.delete(token_hash)
            return None

        return token_data

    def refresh_token(self, refresh_token: str) -> Optional[dict[str, any]]:
        """Use a refresh token to obtain a new access token.

        Validates the refresh token, revokes the old access token,
        and generates a new token pair.

        Args:
            refresh_token: The refresh token to use

        Returns:
            dict | None: New token pair if valid, None if invalid/expired
                Same format as generate_token()

        Examples:
            >>> # Original tokens
            >>> tokens = manager.generate_token(user_id='user123')
            >>> # Wait for access token to expire...
            >>> # Get new tokens
            >>> new_tokens = manager.refresh_token(tokens['refresh_token'])
            >>> if new_tokens:
            ...     print("Got new access token")
        """
        refresh_hash = self._hash_token(refresh_token)
        refresh_data = self.storage.get(refresh_hash)

        if not refresh_data:
            return None

        # Check if it's a refresh token (not access)
        if refresh_data.get('type') != 'refresh':
            return None

        # Check expiration
        expires_at = refresh_data.get('expires_at')
        if not expires_at or expires_at < datetime.utcnow():
            # Refresh token expired, remove from storage
            self.storage.delete(refresh_hash)
            return None

        # Revoke old access token (if it exists)
        old_access_hash = refresh_data.get('access_token_hash')
        if old_access_hash:
            self.storage.delete(old_access_hash)

        # Revoke the refresh token (one-time use)
        self.storage.delete(refresh_hash)

        # Generate new token pair
        return self.generate_token(
            user_id=refresh_data['user_id'],
            scopes=refresh_data.get('scopes', [])
        )

    def revoke_token(self, token: str) -> bool:
        """Revoke a token before its expiration time.

        Can be used for logout or security purposes. Works for both
        access and refresh tokens.

        Args:
            token: The token to revoke

        Returns:
            bool: True if token was found and revoked, False otherwise

        Examples:
            >>> # Logout: revoke access token
            >>> manager.revoke_token(access_token)
            >>> # Also revoke refresh token to prevent new access tokens
            >>> manager.revoke_token(refresh_token)
        """
        token_hash = self._hash_token(token)
        token_data = self.storage.get(token_hash)

        if not token_data:
            return False

        # If revoking a refresh token, also revoke its access token
        if token_data.get('type') == 'refresh':
            access_hash = token_data.get('access_token_hash')
            if access_hash:
                self.storage.delete(access_hash)

        # Delete the token itself
        self.storage.delete(token_hash)
        return True

    def _hash_token(self, token: str) -> str:
        """Hash a token using SHA-256.

        Tokens are hashed before storage so that even if storage
        is compromised, the actual tokens cannot be recovered.

        Args:
            token: Plaintext token

        Returns:
            str: Hexadecimal hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()
