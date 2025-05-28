import os
from cryptography.fernet import Fernet, InvalidToken
from azure.identity import DeviceCodeCredential, TokenCachePersistenceOptions
from core.models.user import User
from sqlalchemy.orm import Session

FERNET_KEY = os.getenv("FERNET_KEY")
if not FERNET_KEY:
    raise RuntimeError("FERNET_KEY environment variable must be set for encryption.")

def get_fernet() -> Fernet:
    return Fernet(FERNET_KEY)

def get_token_cache(user: User) -> bytes:
    """
    Decrypt and return the user's token cache as bytes. Returns b'' if not set.
    """
    if not user.ms_token_cache:
        return b''
    try:
        return get_fernet().decrypt(user.ms_token_cache.encode())
    except InvalidToken:
        raise ValueError("Invalid token cache encryption for user {}".format(user.email))

def set_token_cache(user: User, cache: bytes, session: Session) -> None:
    """
    Encrypt and store the user's token cache. Commits the session.
    """
    user.ms_token_cache = get_fernet().encrypt(cache).decode()
    session.add(user)
    session.commit()

def get_device_code_credential(user: User, session: Session) -> DeviceCodeCredential:
    """
    Return a DeviceCodeCredential using the user's encrypted token cache.
    The token cache is loaded from the user model and persisted back on update.
    """
    from azure.identity import TokenCachePersistenceOptions
    import tempfile
    import uuid
    # Write the decrypted cache to a temp file for use by DeviceCodeCredential
    cache_bytes = get_token_cache(user)
    temp_cache_path = os.path.join(tempfile.gettempdir(), f"msgraph_token_cache_{user.id}_{uuid.uuid4().hex}.bin")
    if cache_bytes:
        with open(temp_cache_path, 'wb') as f:
            f.write(cache_bytes)
    cache_opts = TokenCachePersistenceOptions(
        name=f"msgraph_token_cache_{user.id}",
        allow_unencrypted_storage=True,
        path=temp_cache_path
    )
    credential = DeviceCodeCredential(
        client_id=os.getenv('MS_CLIENT_ID'),
        tenant_id=os.getenv('MS_TENANT_ID'),
        cache_persistence_options=cache_opts
    )
    # Patch the credential to persist the cache back to the user model on update
    orig_get_token = credential._cache._cache._write_cache
    def persist_cache(*args, **kwargs):
        orig_get_token(*args, **kwargs)
        # Read the updated cache and store it encrypted
        with open(temp_cache_path, 'rb') as f:
            updated_cache = f.read()
        set_token_cache(user, updated_cache, session)
    credential._cache._cache._write_cache = persist_cache
    return credential 