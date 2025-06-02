"""
User resolution utility for CLI commands.

Handles user identification with the following precedence:
1. Command-line argument (highest priority)
2. ADMIN_ASSISTANT_USER environment variable
3. OS environment variables (USER, USERNAME, LOGNAME)
"""

import os
from typing import Optional, Union

from core.models.user import User
from core.services.user_service import UserService


def get_os_username() -> Optional[str]:
    """
    Get the current OS username from environment variables.
    
    Checks common OS environment variables in order:
    - USER (Unix/Linux/macOS)
    - USERNAME (Windows)
    - LOGNAME (Unix/Linux fallback)
    
    Returns:
        The OS username if found, None otherwise
    """
    for env_var in ['USER', 'USERNAME', 'LOGNAME']:
        username = os.getenv(env_var)
        if username:
            return username.strip()
    return None


def resolve_user_identifier(cli_user: Optional[Union[str, int]] = None) -> Optional[str]:
    """
    Resolve user identifier following the precedence rules.
    
    Precedence (highest to lowest):
    1. CLI argument (cli_user parameter)
    2. ADMIN_ASSISTANT_USER environment variable
    3. OS environment variables (USER, USERNAME, LOGNAME)
    
    Args:
        cli_user: User identifier from CLI argument (can be username or user ID)
        
    Returns:
        User identifier string, or None if no identifier found
    """
    # 1. CLI argument has highest precedence
    if cli_user is not None:
        return str(cli_user)
    
    # 2. ADMIN_ASSISTANT_USER environment variable
    admin_user = os.getenv('ADMIN_ASSISTANT_USER')
    if admin_user:
        return admin_user.strip()
    
    # 3. OS environment variables
    os_username = get_os_username()
    if os_username:
        return os_username
    
    return None


def resolve_user(cli_user: Optional[Union[str, int]] = None, 
                user_service: Optional[UserService] = None) -> Optional[User]:
    """
    Resolve a User object following the precedence rules.
    
    Args:
        cli_user: User identifier from CLI argument (can be username or user ID)
        user_service: UserService instance (creates new one if None)
        
    Returns:
        User object if found, None otherwise
        
    Raises:
        ValueError: If user identifier is found but no matching user exists
    """
    if user_service is None:
        user_service = UserService()
    
    user_identifier = resolve_user_identifier(cli_user)
    if not user_identifier:
        return None
    
    # Try to resolve as user ID first (if it's numeric)
    try:
        user_id = int(user_identifier)
        user = user_service.get_by_id(user_id)
        if user:
            return user
    except (ValueError, TypeError):
        # Not a numeric ID, continue to username lookup
        pass
    
    # Try to resolve as username
    user = user_service.get_by_username(user_identifier)
    if user:
        return user
    
    # If we get here, the identifier was found but no matching user exists
    raise ValueError(f"No user found for identifier: {user_identifier}")


def get_user_identifier_source(cli_user: Optional[Union[str, int]] = None) -> str:
    """
    Get a description of where the user identifier came from.
    
    Useful for error messages and debugging.
    
    Args:
        cli_user: User identifier from CLI argument
        
    Returns:
        Description string of the identifier source
    """
    if cli_user is not None:
        return "command-line argument"
    
    if os.getenv('ADMIN_ASSISTANT_USER'):
        return "ADMIN_ASSISTANT_USER environment variable"
    
    os_username = get_os_username()
    if os_username:
        for env_var in ['USER', 'USERNAME', 'LOGNAME']:
            if os.getenv(env_var) == os_username:
                return f"{env_var} environment variable"
    
    return "no source found"
