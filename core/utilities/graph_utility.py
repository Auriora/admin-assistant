import os
from msgraph.graph_service_client import GraphServiceClient
from core.models.user import User
from sqlalchemy.orm import Session
from azure.core.credentials import AccessToken

class AccessTokenCredential:
    def __init__(self, access_token: str):
        self._access_token = access_token

    def get_token(self, *scopes, **kwargs):
        # Return an AccessToken object with a far-future expiry (e.g., year 2038)
        return AccessToken(self._access_token, 2**31 - 1)

def get_graph_client(user: User, access_token: str) -> GraphServiceClient:
    """
    Instantiate a GraphServiceClient for the given user using an MSAL access token.
    """
    credential = AccessTokenCredential(access_token)
    scopes = ["https://graph.microsoft.com/.default"]
    return GraphServiceClient(credentials=credential, scopes=scopes) 