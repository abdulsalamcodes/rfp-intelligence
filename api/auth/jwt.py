"""
JWT Token Utilities

Create and verify JWT access and refresh tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import jwt, JWTError

from config.settings import settings


class TokenError(Exception):
    """Token validation error."""
    pass


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data (should include 'sub' for user ID)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )


def create_refresh_token(data: dict) -> str:
    """
    Create a JWT refresh token (longer-lived).
    
    Args:
        data: Payload data (should include 'sub' for user ID)
        
    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    return jwt.encode(
        to_encode,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise TokenError(f"Invalid token: {str(e)}")


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Verify a JWT token and check its type.
    
    Args:
        token: The JWT token to verify
        token_type: Expected token type ('access' or 'refresh')
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenError: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)
    
    if payload.get("type") != token_type:
        raise TokenError(f"Invalid token type. Expected {token_type}")
    
    return payload


def get_token_data(token: str) -> tuple[str, Optional[str]]:
    """
    Extract user_id and org_id from a token.
    
    Args:
        token: The JWT token
        
    Returns:
        Tuple of (user_id, org_id)
    """
    payload = verify_token(token, "access")
    return payload.get("sub"), payload.get("org_id")
