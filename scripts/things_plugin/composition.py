"""The single place where production adapters are connected to use cases."""

from .application import TaskService
from .infrastructure.configuration import FileAuthTokenStore
from .infrastructure.macos import MacOSApplicationLocator, MacOSUriDispatcher
from .infrastructure.uri import ThingsUriBuilder


def create_service() -> TaskService:
    return TaskService(
        uri_builder=ThingsUriBuilder(),
        dispatcher=MacOSUriDispatcher(),
        application_locator=MacOSApplicationLocator(),
        auth_token_store=FileAuthTokenStore(),
    )
