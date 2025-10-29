# genro-auth

> Authentication and authorization library for Genro microservices ecosystem

**genro-auth** provides token-based authentication with refresh capabilities, scope-based authorization, and FastAPI integration for the Genro microservices ecosystem.

## Features

- 🔐 **Token Management** - Generate, validate, and revoke access tokens
- 🔄 **Refresh Tokens** - Long-lived tokens for obtaining new access tokens
- 🎯 **Scope-Based Authorization** - Fine-grained permission control
- ⚡ **FastAPI Integration** - Ready-to-use dependencies for FastAPI
- 💾 **Multiple Storage Backends** - Memory (dev) and Redis (production)
- 🧪 **Easy Testing** - Mock tokens for unit tests
- 🔒 **Secure by Default** - Token hashing, expiration, revocation

## Installation

```bash
# Basic installation
pip install genro-auth

# With Redis support
pip install genro-auth[redis]
```

## Quick Start

### Basic Usage

```python
from genro_auth import TokenManager
from genro_auth.storage import MemoryTokenStorage

# Initialize token manager
storage = MemoryTokenStorage()
token_manager = TokenManager(
    token_ttl=3600,      # 1 hour access token
    refresh_ttl=86400,   # 24 hours refresh token
    storage_backend=storage
)

# Generate token pair
tokens = token_manager.generate_token(
    user_id='user123',
    scopes=['storage.read', 'storage.write']
)

print(tokens)
# {
#     'access_token': '...',
#     'refresh_token': '...',
#     'expires_in': 3600,
#     'token_type': 'Bearer'
# }

# Validate token
user_data = token_manager.validate_token(tokens['access_token'])
print(user_data)
# {
#     'user_id': 'user123',
#     'scopes': ['storage.read', 'storage.write'],
#     'type': 'access',
#     'expires_at': datetime(...)
# }

# Refresh token
new_tokens = token_manager.refresh_token(tokens['refresh_token'])

# Revoke token
token_manager.revoke_token(tokens['access_token'])
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from genro_auth import TokenManager
from genro_auth.fastapi import create_auth_dependency, create_scope_dependency
from genro_auth.storage import MemoryTokenStorage

app = FastAPI()
token_manager = TokenManager(storage_backend=MemoryTokenStorage())

# Create auth dependency
require_auth = create_auth_dependency(token_manager)
require_admin = create_scope_dependency(['admin'])

@app.post("/login")
async def login(username: str, password: str):
    """Generate access token."""
    # Your credential validation logic here
    if not validate_credentials(username, password):
        raise HTTPException(401, "Invalid credentials")

    return token_manager.generate_token(
        user_id=username,
        scopes=['read', 'write']
    )

@app.get("/protected")
async def protected_route(user_data: dict = Depends(require_auth)):
    """Protected endpoint - requires valid token."""
    return {"message": f"Hello {user_data['user_id']}"}

@app.get("/admin")
async def admin_route(user_data: dict = Depends(require_admin)):
    """Admin endpoint - requires 'admin' scope."""
    return {"message": "Admin access granted"}

@app.post("/refresh")
async def refresh(refresh_token: str):
    """Refresh access token."""
    new_tokens = token_manager.refresh_token(refresh_token)
    if not new_tokens:
        raise HTTPException(401, "Invalid refresh token")
    return new_tokens

@app.post("/logout")
async def logout(user_data: dict = Depends(require_auth)):
    """Revoke current token."""
    # Get token from request (implementation depends on your setup)
    token_manager.revoke_token(current_token)
    return {"ok": True}
```

### Production Setup with Redis

```python
import redis
from genro_auth import TokenManager
from genro_auth.storage import RedisTokenStorage

# Connect to Redis
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

# Use Redis storage
storage = RedisTokenStorage(redis_client)
token_manager = TokenManager(
    token_ttl=3600,
    refresh_ttl=86400,
    storage_backend=storage
)
```

## Storage Backends

### Memory Storage

For development and testing:

```python
from genro_auth.storage import MemoryTokenStorage

storage = MemoryTokenStorage()
```

**Pros**: No dependencies, fast
**Cons**: Not persistent, not scalable

### Redis Storage

For production:

```python
import redis
from genro_auth.storage import RedisTokenStorage

redis_client = redis.Redis(host='localhost', port=6379)
storage = RedisTokenStorage(redis_client)
```

**Pros**: Persistent, scalable, automatic expiration
**Cons**: Requires Redis server

### Custom Storage

Implement your own backend:

```python
from genro_auth.storage import TokenStorage

class CustomStorage(TokenStorage):
    def set(self, key: str, value: dict):
        # Your implementation
        pass

    def get(self, key: str) -> dict | None:
        # Your implementation
        pass

    def delete(self, key: str):
        # Your implementation
        pass
```

## Scopes

Use scopes for fine-grained authorization:

```python
# Generate token with scopes
tokens = token_manager.generate_token(
    user_id='user123',
    scopes=['storage.read', 'storage.write', 'storage.delete']
)

# Check scopes in FastAPI
from genro_auth.fastapi import create_scope_dependency

require_write = create_scope_dependency(['storage.write'])

@app.put("/files/{path}")
async def upload_file(
    path: str,
    data: bytes,
    user_data: dict = Depends(require_write)
):
    # Only users with storage.write scope can access
    ...
```

**Common scope patterns:**
- `resource.action` - e.g., `storage.read`, `mail.send`
- `admin` - Full administrative access
- `read`, `write`, `delete` - Generic permissions

## Testing

### Mock Tokens for Tests

```python
import pytest
from genro_auth import TokenManager
from genro_auth.storage import MemoryTokenStorage

@pytest.fixture
def token_manager():
    return TokenManager(storage_backend=MemoryTokenStorage())

def test_protected_endpoint(token_manager):
    # Generate test token
    tokens = token_manager.generate_token(
        user_id='test_user',
        scopes=['read']
    )

    # Use in test
    response = client.get(
        "/protected",
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )

    assert response.status_code == 200
```

## Configuration

### Environment Variables

```bash
# Token lifetimes (seconds)
AUTH_TOKEN_TTL=3600        # 1 hour
AUTH_REFRESH_TTL=86400     # 24 hours

# Redis (if using)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=optional
```

### Programmatic Configuration

```python
token_manager = TokenManager(
    token_ttl=3600,          # Access token lifetime (seconds)
    refresh_ttl=86400,       # Refresh token lifetime (seconds)
    storage_backend=storage  # Storage backend instance
)
```

## Security Considerations

1. **Token Storage**: Tokens are hashed (SHA-256) before storage
2. **Expiration**: Both access and refresh tokens expire
3. **Revocation**: Tokens can be revoked before expiration
4. **HTTPS**: Always use HTTPS in production
5. **Token Rotation**: Refreshing revokes old access token
6. **Secrets**: Use strong, random tokens (32 bytes)

## Architecture

```
┌─────────────────────────────────────┐
│         Your Application            │
└──────────┬──────────────────────────┘
           │
           ↓
┌─────────────────────────────────────┐
│         genro-auth                  │
│  ┌─────────────┐  ┌──────────────┐ │
│  │TokenManager │  │  FastAPI     │ │
│  │             │  │ Dependencies │ │
│  └──────┬──────┘  └──────────────┘ │
│         │                           │
│         ↓                           │
│  ┌─────────────────────────────┐   │
│  │    Storage Backend          │   │
│  │  (Memory / Redis / Custom)  │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## Examples

See the [examples/](examples/) directory for complete working examples:

- `basic_usage.py` - Token generation and validation
- `fastapi_app.py` - Complete FastAPI integration
- `redis_setup.py` - Production Redis configuration
- `custom_storage.py` - Implementing custom storage backend

## API Reference

See [API Documentation](https://genro-auth.readthedocs.io) for detailed API reference.

## Development

```bash
# Clone repository
git clone https://github.com/genropy/genro-auth
cd genro-auth

# Install development dependencies
pip install -e ".[dev,redis]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=genro_auth --cov-report=html

# Format code
black genro_auth tests

# Lint
ruff check genro_auth tests

# Type check
mypy genro_auth
```

## Roadmap

- [x] Token generation and validation
- [x] Refresh token support
- [x] Scope-based authorization
- [x] FastAPI dependencies
- [x] Memory storage backend
- [x] Redis storage backend
- [ ] JWT support (in addition to opaque tokens)
- [ ] OAuth2 integration helpers
- [ ] Rate limiting per token
- [ ] Token usage audit logging
- [ ] Database storage backend (PostgreSQL, SQLite)

## Related Projects

- [genro-storage](https://github.com/genropy/genro-storage) - Storage abstraction layer
- [genro-storage-proxy](https://github.com/genropy/genro-storage-proxy) - Storage HTTP microservice
- [genro-mail-proxy](https://github.com/genropy/genro-mail-proxy) - Email service

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- Documentation: https://genro-auth.readthedocs.io
- Issues: https://github.com/genropy/genro-auth/issues
- Discussions: https://github.com/genropy/genro-auth/discussions
