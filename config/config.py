"""Centralized configuration management for the OAP project.

The Config class loads runtime settings from environment variables and an
optional ``env`` file located at the project root. Environment variables always
win, while the file acts as a convenient local secret store. The file accepts
``KEY=VALUE`` pairs (preferred) or, for backward compatibility, three bare lines
representing ``SMTP_USER``, ``SMTP_PASSWORD``, and ``API_KEY`` in that order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from threading import Lock
from typing import Dict, Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _coerce_path(value: str | Path, base: Path) -> Path:
    """Return an absolute Path, resolving relative strings against ``base``."""
    path = Path(value)
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


@dataclass(slots=True)
class _ConfigData:
    events_dir: Path = field(default_factory=lambda: (_PROJECT_ROOT / "events"))
    recipient_list_file: Path = field(default_factory=lambda: (_PROJECT_ROOT / "List.txt"))
    env_file: Path = field(default_factory=lambda: (_PROJECT_ROOT / "env"))
    smtp_server: str = "smtp.163.com"
    smtp_port: int = 465
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    api_key: Optional[str] = None


class Config:
    """Singleton providing typed access to project configuration."""

    _instance: Optional["Config"] = None
    _lock: Lock = Lock()

    def __new__(cls, env_file: str | Path | None = None) -> "Config":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._data = _ConfigData()
                    cls._instance._loaded = False
        return cls._instance

    def __init__(self, env_file: str | Path | None = None) -> None:
        if self._loaded:
            return
        if env_file is not None:
            self._data.env_file = _coerce_path(env_file, _PROJECT_ROOT)
        self._load()
        self._loaded = True

    # ------------------------------------------------------------------
    # Public attributes and helpers
    # ------------------------------------------------------------------
    @property
    def events_dir(self) -> Path:
        return _coerce_path(os.getenv("EVENTS_DIR", self._data.events_dir), _PROJECT_ROOT)

    @property
    def recipient_list_file(self) -> Path:
        return _coerce_path(os.getenv("RECIPIENT_LIST", self._data.recipient_list_file), _PROJECT_ROOT)

    @property
    def smtp_server(self) -> str:
        return os.getenv("SMTP_SERVER", self._data.smtp_server)

    @property
    def smtp_port(self) -> int:
        value = os.getenv("SMTP_PORT")
        try:
            return int(value) if value is not None else self._data.smtp_port
        except ValueError:
            return self._data.smtp_port

    @property
    def smtp_user(self) -> Optional[str]:
        return os.getenv("SMTP_USER", self._data.smtp_user)

    @property
    def smtp_password(self) -> Optional[str]:
        return os.getenv("SMTP_PASSWORD", self._data.smtp_password)

    @property
    def api_key(self) -> Optional[str]:
        raw = os.getenv("API_KEY", self._data.api_key)
        if raw and raw.startswith("Bearer "):
            return raw.split(" ", 1)[1]
        return raw

    @property
    def ai_headers(self) -> Dict[str, str]:
        """Return default headers for AI API calls."""
        if not self.api_key:
            return {"Content-Type": "application/json"}
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def ensure_directories(self) -> None:
        """Ensure directories that must exist at runtime are created."""
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def reload(self) -> None:
        """Reload configuration from environment and env file."""
        with self._lock:
            self._load(force=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load(self, force: bool = False) -> None:
        if not force and getattr(self, "_loaded", False):
            return
        self._load_from_env_file(self._data.env_file)

    def _load_from_env_file(self, env_file: Path) -> None:
        if not env_file.exists():
            return
        fallback_keys = ["SMTP_USER", "SMTP_PASSWORD", "API_KEY"]
        fallback_index = 0
        try:
            for raw_line in env_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip().upper()
                    value = value.strip()
                elif fallback_index < len(fallback_keys):
                    key = fallback_keys[fallback_index]
                    value = line
                    fallback_index += 1
                else:
                    continue
                if key == "SMTP_USER":
                    self._data.smtp_user = value or None
                elif key == "SMTP_PASSWORD":
                    self._data.smtp_password = value or None
                elif key == "API_KEY":
                    token = value.replace("Bearer ", "", 1)
                    self._data.api_key = token or None
                elif key == "SMTP_SERVER":
                    if value:
                        self._data.smtp_server = value
                elif key == "SMTP_PORT":
                    try:
                        self._data.smtp_port = int(value)
                    except ValueError:
                        pass
                elif key == "EVENTS_DIR":
                    self._data.events_dir = _coerce_path(value, _PROJECT_ROOT)
                elif key == "RECIPIENT_LIST":
                    self._data.recipient_list_file = _coerce_path(value, _PROJECT_ROOT)
        except OSError as exc:
            raise RuntimeError(f"Failed to read configuration file: {env_file}") from exc


__all__ = ["Config"]
