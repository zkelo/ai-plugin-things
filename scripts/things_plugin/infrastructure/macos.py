"""macOS delivery and read-only application discovery adapters."""

import platform
import plistlib
import subprocess
from pathlib import Path
from typing import Callable, Optional, Sequence

from ..application import ApplicationStatus, DispatchError

BUNDLE_ID = "com.culturedcode.ThingsMac"
DISPATCH_TIMEOUT_SECONDS = 15
APPLICATION_ROOTS = (Path("/Applications"), Path.home() / "Applications")
ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


class MacOSUriDispatcher:
    def __init__(
        self,
        process_runner: Optional[ProcessRunner] = None,
        platform_name: Optional[Callable[[], str]] = None,
    ) -> None:
        self._process_runner = (
            process_runner if process_runner is not None else subprocess.run
        )
        self._platform_name = (
            platform_name if platform_name is not None else platform.system
        )

    def dispatch(self, uri: str) -> None:
        if self._platform_name() != "Darwin":
            raise DispatchError(
                "Automatic dispatch requires macOS with Things 3 installed; use preview to obtain the URI."
            )
        command = ["/usr/bin/open", "-b", BUNDLE_ID, uri]
        try:
            result = self._process_runner(
                command,
                capture_output=True,
                text=True,
                timeout=DISPATCH_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise DispatchError(
                "Dispatch timed out. Delivery is unknown; inspect Things before retrying to avoid duplicates.",
                delivery_unknown=True,
            ) from None
        except OSError as error:
            detail = f" (OS error {error.errno})" if error.errno is not None else ""
            raise DispatchError(
                f"Cannot start the Things URI dispatcher{detail}."
            ) from None
        if result.returncode:
            raise DispatchError(
                f"macOS open returned exit code {result.returncode}. Delivery is unknown; inspect Things before retrying.",
                delivery_unknown=True,
            )


class MacOSApplicationLocator:
    def __init__(
        self,
        application_roots: Optional[Sequence[Path]] = None,
        platform_name: Optional[Callable[[], str]] = None,
    ) -> None:
        self._application_roots = (
            tuple(application_roots)
            if application_roots is not None
            else APPLICATION_ROOTS
        )
        self._platform_name = (
            platform_name if platform_name is not None else platform.system
        )

    def locate(self) -> ApplicationStatus:
        current_platform = self._platform_name()
        if current_platform != "Darwin":
            return ApplicationStatus(current_platform, BUNDLE_ID)
        for root in self._application_roots:
            for application in root.glob("*.app"):
                if self._bundle_identifier(application) == BUNDLE_ID:
                    return ApplicationStatus(
                        current_platform, BUNDLE_ID, str(application)
                    )
        return ApplicationStatus(current_platform, BUNDLE_ID)

    @staticmethod
    def _bundle_identifier(application: Path) -> Optional[str]:
        info_path = application / "Contents" / "Info.plist"
        try:
            with info_path.open("rb") as handle:
                info = plistlib.load(handle)
        except (OSError, ValueError, plistlib.InvalidFileException):
            return None
        if not isinstance(info, dict):
            return None
        identifier = info.get("CFBundleIdentifier")
        return identifier if isinstance(identifier, str) else None
