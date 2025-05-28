import os
from msgraph.graph_service_client import GraphServiceClient
from core.models.user import User
from sqlalchemy.orm import Session
from core.utilities.auth_utility import get_device_code_credential

def get_graph_client(user: User, session: Session) -> GraphServiceClient:
    """
    Instantiate a GraphServiceClient for the given user using DeviceCodeCredential from auth_utility.
    """
    scopes = ["https://graph.microsoft.com/.default"]
    credential = get_device_code_credential(user, session)
    return GraphServiceClient(credentials=credential, scopes=scopes) 