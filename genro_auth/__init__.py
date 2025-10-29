"""genro-auth - Authentication and authorization for Genro microservices.

This package provides token-based authentication with refresh capabilities,
scope-based authorization, and FastAPI integration.

Main Components:
    - TokenManager: Generate, validate, refresh, and revoke tokens
    - TokenStorage: Abstract base and implementations (Memory, Redis)
    - FastAPI integration: Ready-to-use dependencies

Quick Start:
    >>> from genro_auth import TokenManager
    >>> from genro_auth.storage import MemoryTokenStorage
    >>>
    >>> # Initialize
    >>> storage = MemoryTokenStorage()
    >>> token_manager = TokenManager(storage_backend=storage)
    >>>
    >>> # Generate tokens
    >>> tokens = token_manager.generate_token(
    ...     user_id='user123',
    ...     scopes=['read', 'write']
    ... )
    >>>
    >>> # Validate token
    >>> user_data = token_manager.validate_token(tokens['access_token'])
    >>> print(user_data['user_id'])  # 'user123'

For FastAPI integration:
    >>> from genro_auth.fastapi import create_auth_dependency
    >>> require_auth = create_auth_dependency(token_manager)
    >>> @app.get("/protected")
    >>> async def route(user_data: dict = Depends(require_auth)):
    ...     return {"user": user_data['user_id']}

For more information, see the documentation at:
https://genro-auth.readthedocs.io
"""

__version__ = '0.1.0'

from .tokens import TokenManager
from .storage import TokenStorage, MemoryTokenStorage

__all__ = [
    # Version
    '__version__',

    # Main classes
    'TokenManager',

    # Storage
    'TokenStorage',
    'MemoryTokenStorage',
]

# Conditional exports for optional dependencies
try:
    from .storage import RedisTokenStorage
    __all__.append('RedisTokenStorage')
except ImportError:
    pass

try:
    from .fastapi import create_auth_dependency, create_scope_dependency
    __all__.extend(['create_auth_dependency', 'create_scope_dependency'])
except ImportError:
    pass
