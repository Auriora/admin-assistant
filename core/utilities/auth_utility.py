import os
import msal
from core.models.user import User

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "admin-assistant")
CACHE_PATH = os.path.join(CACHE_DIR, "ms_token.json")
SCOPES = ["https://graph.microsoft.com/.default"]


def get_msal_app():
    client_id = os.getenv("MS_CLIENT_ID")
    tenant_id = os.getenv("MS_TENANT_ID")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_PATH):
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
    # Save the cache
    with open(CACHE_PATH, "w") as f:
        f.write(cache.serialize())
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