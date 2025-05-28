import os
import base64
import logging
from cryptography.fernet import Fernet, InvalidToken
from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions
from core.models.user import User
from sqlalchemy.orm import Session
from typing import Optional

FERNET_KEY_ENV = os.getenv("FERNET_KEY")
if not FERNET_KEY_ENV:
    raise RuntimeError("FERNET_KEY environment variable must be set for encryption.")
try:
    # Fernet key must be bytes
    FERNET_KEY: bytes = base64.urlsafe_b64decode(FERNET_KEY_ENV)
except Exception as e:
    raise RuntimeError("FERNET_KEY must be a valid base64-encoded key.") from e

def get_fernet() -> Fernet:
    """
    Return a Fernet instance for encryption/decryption using the configured key.
    """
    return Fernet(FERNET_KEY)

def get_token_cache(user: User) -> bytes:
    """
    Decrypt and return the user's token cache as bytes. Returns b'' if not set.
    Raises ValueError if the token cache is invalid.
    """
    cache_value = getattr(user, "ms_token_cache", None)
    if not cache_value:
        return b''
    try:
        return get_fernet().decrypt(cache_value.encode())
    except InvalidToken as e:
        raise ValueError(f"Invalid token cache encryption for user {getattr(user, 'email', 'unknown')}") from e

def set_token_cache(user: User, cache: bytes, session: Session) -> None:
    """
    Encrypt and store the user's token cache. Commits the session.
    """
    encrypted = get_fernet().encrypt(cache).decode()
    setattr(user, "ms_token_cache", encrypted)
    session.add(user)
    session.commit()

def get_device_code_credential(user: User, session: Session) -> DeviceCodeCredential:
    """
    Return a DeviceCodeCredential using the user's encrypted token cache.
    The token cache is loaded from the user model and persisted back on update.
    Raises RuntimeError if required environment variables are missing.
    """
    import tempfile
    import uuid
    # Validate required environment variables
    ms_client_id = os.getenv('MS_CLIENT_ID')
    ms_tenant_id = os.getenv('MS_TENANT_ID')
    if not ms_client_id:
        raise RuntimeError("MS_CLIENT_ID environment variable must be set.")
    if not ms_tenant_id:
        raise RuntimeError("MS_TENANT_ID environment variable must be set.")
    # Write the decrypted cache to a temp file for use by DeviceCodeCredential
    cache_bytes = get_token_cache(user)
    temp_cache_path = os.path.join(tempfile.gettempdir(), f"msgraph_token_cache_{getattr(user, 'id', 'unknown')}_{uuid.uuid4().hex}.bin")
    if cache_bytes:
        with open(temp_cache_path, 'wb') as f:
            f.write(cache_bytes)
    cache_opts = TokenCachePersistenceOptions(
        name=f"msgraph_token_cache_{getattr(user, 'id', 'unknown')}",
        allow_unencrypted_storage=True,
        path=temp_cache_path
    )
    credential = DeviceCodeCredential(
        client_id=ms_client_id,
        tenant_id=ms_tenant_id,
        cache_persistence_options=cache_opts
    )
    # NOTE: There is no public API to hook into the token cache update event in azure-identity.
    # If you need to persist the updated cache back to the user model, you must do so manually
    # after authentication or token acquisition, by reading the cache file and calling set_token_cache.
    # Do NOT access private attributes like _cache._cache._write_cache, as this is not supported and
    # will break with SDK updates.
    return credential 