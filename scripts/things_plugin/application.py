"""Task creation scenarios, independent of URI syntax and operating systems."""

import unicodedata
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Optional, Protocol, Sequence, Tuple

from .domain import Task, ValidationError

AUTH_TOKEN_MAX_LENGTH = 4000


class AuthenticationError(ValueError):
    """A missing or invalid Things credential, without its sensitive value."""


@dataclass(frozen=True)
class AuthToken:
    """A validated Things credential whose representation never exposes it."""

    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise AuthenticationError("The Things key must be a string.")
        if len(self.value) > AUTH_TOKEN_MAX_LENGTH:
            raise AuthenticationError("The Things key exceeds 4000 characters.")
        if any(unicodedata.category(char) in ("Cc", "Cf") for char in self.value):
            raise AuthenticationError("The Things key contains control characters.")
        normalized = self.value.strip()
        if not normalized:
            raise AuthenticationError("The Things key must not be empty.")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class TaskOptions:
    reveal: bool = False
    show_quick_entry: bool = False

    def __post_init__(self) -> None:
        for name, value in (
            ("reveal", self.reveal),
            ("show_quick_entry", self.show_quick_entry),
        ):
            if not isinstance(value, bool):
                raise ValidationError(f"{name} must be a boolean.")


@dataclass(frozen=True)
class PreparedUri:
    """Keep the authenticated transport separate from its safe public preview."""

    uri: str = field(repr=False)
    display_uri: str


class DeliveryStatus(str, Enum):
    PREVIEW = "preview"
    DISPATCHED = "dispatched"


@dataclass(frozen=True)
class DeliveryResult:
    status: DeliveryStatus
    uri: str
    titles: Tuple[str, ...]

    @property
    def creation_verified(self) -> bool:
        return False


@dataclass(frozen=True)
class ApplicationStatus:
    platform: str
    bundle_id: str
    app_path: Optional[str] = None
    auth_token_configured: bool = False

    @property
    def app_found(self) -> bool:
        return self.app_path is not None


class DispatchError(RuntimeError):
    """A failed handoff, optionally with an uncertain delivery outcome."""

    def __init__(self, message: str, *, delivery_unknown: bool = False) -> None:
        super().__init__(message)
        self.delivery_unknown = delivery_unknown


class AuthTokenStore(Protocol):
    def get(self) -> Optional[AuthToken]: ...

    def save(self, token: AuthToken) -> None: ...


class UriBuilder(Protocol):
    def build_task(
        self, task: Task, options: TaskOptions, token: AuthToken
    ) -> PreparedUri: ...

    def build_tasks(
        self, tasks: Sequence[Task], reveal: bool, token: AuthToken
    ) -> PreparedUri: ...


class UriDispatcher(Protocol):
    def dispatch(self, uri: str) -> None: ...


class ApplicationLocator(Protocol):
    def locate(self) -> ApplicationStatus: ...


class TaskService:
    """Authenticate every request before URI construction and its single handoff."""

    def __init__(
        self,
        uri_builder: UriBuilder,
        dispatcher: UriDispatcher,
        application_locator: ApplicationLocator,
        auth_token_store: AuthTokenStore,
    ) -> None:
        self._uri_builder = uri_builder
        self._dispatcher = dispatcher
        self._application_locator = application_locator
        self._auth_token_store = auth_token_store

    def add_task(
        self, task: Task, options: TaskOptions, preview: bool = False
    ) -> DeliveryResult:
        self._validate_boolean(preview, "preview")
        if options.show_quick_entry:
            raise ValidationError(
                "Authenticated task creation does not support Quick Entry."
            )
        token = self._require_auth_token()
        prepared = self._uri_builder.build_task(task, options, token)
        return self._deliver(prepared, (task.title,), preview)

    def add_tasks(
        self, tasks: Sequence[Task], preview: bool = False, reveal: bool = False
    ) -> DeliveryResult:
        self._validate_boolean(preview, "preview")
        self._validate_boolean(reveal, "reveal")
        token = self._require_auth_token()
        task_snapshot = tuple(tasks)
        prepared = self._uri_builder.build_tasks(task_snapshot, reveal, token)
        return self._deliver(
            prepared, tuple(task.title for task in task_snapshot), preview
        )

    def get_status(self) -> ApplicationStatus:
        status = self._application_locator.locate()
        return replace(
            status, auth_token_configured=self._auth_token_store.get() is not None
        )

    def configure_auth_token(self, value: str) -> None:
        self._auth_token_store.save(AuthToken(value))

    def _require_auth_token(self) -> AuthToken:
        token = self._auth_token_store.get()
        if token is None:
            raise AuthenticationError(
                "A Things key is required. Configure it before creating or previewing tasks."
            )
        return token

    def _deliver(
        self, prepared: PreparedUri, titles: Tuple[str, ...], preview: bool
    ) -> DeliveryResult:
        if preview:
            return DeliveryResult(DeliveryStatus.PREVIEW, prepared.display_uri, titles)
        self._dispatcher.dispatch(prepared.uri)
        return DeliveryResult(DeliveryStatus.DISPATCHED, prepared.display_uri, titles)

    @staticmethod
    def _validate_boolean(value: bool, name: str) -> None:
        if not isinstance(value, bool):
            raise ValidationError(f"{name} must be a boolean.")
