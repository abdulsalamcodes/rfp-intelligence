"""
Authentication Package

JWT-based authentication with multi-tenant support.
"""

from api.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    decode_token
)
from api.auth.password import (
    hash_password,
    verify_password
)
from api.auth.dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_org,
    require_roles
)

__all__ = [
    # JWT
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "decode_token",
    # Password
    "hash_password",
    "verify_password",
    # Dependencies
    "get_current_user",
    "get_current_active_user",
    "get_current_org",
    "require_roles"
]
