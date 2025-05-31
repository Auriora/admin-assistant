import os
import msal
import stat
from core.models.user import User

# Secure cache directory with restricted permissions
CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "admin-assistant")
CACHE_PATH = os.path.join(CACHE_DIR, "ms_token.json")
SCOPES = ["https://graph.microsoft.com/.default"]

def ensure_secure_cache_dir():
    """Ensure cache directory exists with secure permissions."""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, mode=0o700, exist_ok=True)  # Owner read/write/execute only
    else:
        # Ensure existing directory has secure permissions
        os.chmod(CACHE_DIR, 0o700)


def get_msal_app():
    """Get MSAL application with secure token cache."""
    client_id = os.getenv("MS_CLIENT_ID")
    tenant_id = os.getenv("MS_TENANT_ID")

    if not client_id or not tenant_id:
        raise ValueError("MS_CLIENT_ID and MS_TENANT_ID environment variables are required")

    authority = f"https://login.microsoftonline.com/{tenant_id}"

    # Ensure secure cache directory
    ensure_secure_cache_dir()

    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_PATH):
        # Verify file permissions before reading
        file_stat = os.stat(CACHE_PATH)
        if file_stat.st_mode & 0o077:  # Check if group/other have any permissions
            print("WARNING: Token cache file has insecure permissions. Fixing...")
            os.chmod(CACHE_PATH, 0o600)  # Owner read/write only

        with open(CACHE_PATH, "r") as f:
            cache.deserialize(f.read())

    app = msal.PublicClientApplication(
        client_id=client_id,
        authority=authority,
        token_cache=cache
    )
    return app, cache


def msal_login():
    app, cache = get_msal_app()
    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError("Failed to create device flow")
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)
    # Save the cache with secure permissions
    with open(CACHE_PATH, "w") as f:
        f.write(cache.serialize())

    # Set secure file permissions (owner read/write only)
    os.chmod(CACHE_PATH, 0o600)

    if "access_token" not in result:
        raise RuntimeError("Failed to acquire token: %s" % result.get("error_description"))
    return result


def msal_logout():
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)


def get_cached_access_token():
    app, cache = get_msal_app()
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            return result["access_token"]
    return None 