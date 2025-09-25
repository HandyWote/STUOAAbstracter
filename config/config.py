"""Simple configuration loader for the OAP project."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class Config:
    """Load runtime settings from ``env`` and environment variables."""

    def __init__(self, env_file: str | Path | None = None) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        default_env = self.project_root / "env"
        self.env_file = self._resolve_path(env_file) if env_file else default_env

        # Defaults that work for local development out of the box
        self.events_dir: Path = self.project_root / "events"
        self.recipient_list_file: Path = self.project_root / "List.txt"
        self.smtp_server: str = "smtp.163.com"
        self.smtp_port: int = 465
        self.smtp_user: Optional[str] = None
        self.smtp_password: Optional[str] = None
        self.api_key: Optional[str] = None

        self.load()

    # ------------------------------------------------------------------
    # Public helpers used by Sender/OA
    # ------------------------------------------------------------------
    def load(self) -> None:
        """Populate configuration values from file and environment."""
        self._load_from_env_file()
        self._override_with_environment()

    def reload(self) -> None:
        """Force a fresh read of configuration sources."""
        self.load()

    def ensure_directories(self) -> None:
        self.events_dir.mkdir(parents=True, exist_ok=True)

    @property
    def ai_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_path(self, value: str | Path) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    def _load_from_env_file(self) -> None:
        if not self.env_file.exists():
            return

        fallback_keys = ["SMTP_USER", "SMTP_PASSWORD", "API_KEY"]
        fallback_index = 0

        try:
            for raw_line in self.env_file.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, raw_value = line.split("=", 1)
                    key = key.strip().upper()
                    value = raw_value.strip()
                else:
                    if fallback_index >= len(fallback_keys):
                        continue
                    key = fallback_keys[fallback_index]
                    value = line
                    fallback_index += 1

                self._apply_setting(key, value)
        except OSError as exc:
            raise RuntimeError(f"无法读取配置文件: {self.env_file}") from exc

    def _override_with_environment(self) -> None:
        keys = [
            "EVENTS_DIR",
            "RECIPIENT_LIST",
            "SMTP_SERVER",
            "SMTP_PORT",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "API_KEY",
        ]
        for key in keys:
            value = os.getenv(key)
            if value is not None and value != "":
                self._apply_setting(key, value)

    def _apply_setting(self, key: str, raw_value: str) -> None:
        value = raw_value.strip()
        if key == "EVENTS_DIR":
            self.events_dir = self._resolve_path(value)
        elif key == "RECIPIENT_LIST":
            self.recipient_list_file = self._resolve_path(value)
        elif key == "SMTP_SERVER":
            if value:
                self.smtp_server = value
        elif key == "SMTP_PORT":
            try:
                self.smtp_port = int(value)
            except ValueError:
                pass
        elif key == "SMTP_USER":
            self.smtp_user = value or None
        elif key == "SMTP_PASSWORD":
            self.smtp_password = value or None
        elif key == "API_KEY":
            token = value.replace("Bearer ", "", 1)
            self.api_key = token or None


__all__ = ["Config"]
