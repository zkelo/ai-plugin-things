"""Local credential persistence behind the application's credential boundary."""

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from ..application import AuthenticationError, AuthToken

TOKEN_ENVIRONMENT_VARIABLE = "THINGS_AUTH_TOKEN"
CONFIG_ENVIRONMENT_VARIABLE = "THINGS_URI_CONFIG_FILE"
TOKEN_CONFIGURATION_FIELD = "auth_token"


class FileAuthTokenStore:
    """Reread credentials on demand; atomically save a private local JSON file."""

    def __init__(
        self,
        path: Optional[Path] = None,
        environment: Optional[Mapping[str, str]] = None,
    ) -> None:
        self._environment = os.environ if environment is None else environment
        if path is None:
            configured_path = self._environment.get(CONFIG_ENVIRONMENT_VARIABLE)
            path = (
                Path(configured_path).expanduser()
                if configured_path
                else Path.home() / ".config" / "things-uri" / "config.json"
            )
        self._path = path

    def get(self) -> Optional[AuthToken]:
        environment_value = self._environment.get(TOKEN_ENVIRONMENT_VARIABLE)
        if environment_value:
            return AuthToken(environment_value)
        value = self._load_document().get(TOKEN_CONFIGURATION_FIELD)
        return None if value is None else AuthToken(value)

    def save(self, token: AuthToken) -> None:
        if self._environment.get(TOKEN_ENVIRONMENT_VARIABLE):
            raise AuthenticationError(
                "THINGS_AUTH_TOKEN takes precedence. Remove it before saving a local Things key."
            )
        document = self._load_document()
        document[TOKEN_CONFIGURATION_FIELD] = token.value
        self._save_document(document)

    def _load_document(self) -> Dict[str, Any]:
        if not self._validate_existing_file():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as source:
                document = json.load(source)
        except (json.JSONDecodeError, UnicodeError):
            raise AuthenticationError(
                "The local Things configuration is invalid JSON."
            ) from None
        except OSError:
            raise RuntimeError("Cannot read the local Things configuration.") from None
        if not isinstance(document, dict):
            raise AuthenticationError(
                "The local Things configuration must be a JSON object."
            )
        return document

    def _validate_existing_file(self) -> bool:
        try:
            metadata = self._path.lstat()
        except FileNotFoundError:
            return False
        except OSError:
            raise RuntimeError(
                "Cannot inspect the local Things configuration."
            ) from None
        if not stat.S_ISREG(metadata.st_mode):
            raise AuthenticationError(
                "The local Things configuration must be a regular file, not a symbolic link."
            )
        if hasattr(os, "getuid") and metadata.st_uid != os.getuid():
            raise AuthenticationError(
                "The local Things configuration must belong to this user."
            )
        return True

    def _save_document(self, document: Dict[str, Any]) -> None:
        temporary_path: Optional[Path] = None
        try:
            self._create_private_directories(self._path.parent)
            descriptor, name = tempfile.mkstemp(
                prefix=".things-uri-", suffix=".tmp", dir=self._path.parent
            )
            temporary_path = Path(name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as target:
                os.fchmod(target.fileno(), 0o600)
                json.dump(document, target, ensure_ascii=False, indent=2)
                target.write("\n")
                target.flush()
                os.fsync(target.fileno())
            self._validate_existing_file()
            os.replace(temporary_path, self._path)
        except OSError:
            raise RuntimeError("Cannot save the local Things configuration.") from None
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    @staticmethod
    def _create_private_directories(directory: Path) -> None:
        missing: List[Path] = []
        current = directory
        while not current.exists():
            missing.append(current)
            current = current.parent
        for ancestor in reversed(missing):
            ancestor.mkdir(mode=0o700)
            ancestor.chmod(0o700)
