from __future__ import annotations

import os
from dataclasses import dataclass

from .matriks import MatriksEndpointConfig, MatriksRestProvider


@dataclass(frozen=True, slots=True)
class MatriksSettings:
    base_url: str
    api_key: str
    symbols_path: str
    metadata_path: str
    history_path: str
    latest_path: str
    health_path: str | None = None

    @classmethod
    def from_env(cls) -> MatriksSettings:
        values = {
            "base_url": os.getenv("MATRIX_API_BASE_URL"),
            "api_key": os.getenv("MATRIX_API_KEY"),
            "symbols_path": os.getenv("MATRIX_SYMBOLS_PATH"),
            "metadata_path": os.getenv("MATRIX_METADATA_PATH"),
            "history_path": os.getenv("MATRIX_HISTORY_PATH"),
            "latest_path": os.getenv("MATRIX_LATEST_PATH"),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing Matriks configuration: " + ", ".join(missing)
            )

        return cls(
            base_url=values["base_url"],
            api_key=values["api_key"],
            symbols_path=values["symbols_path"],
            metadata_path=values["metadata_path"],
            history_path=values["history_path"],
            latest_path=values["latest_path"],
            health_path=os.getenv("MATRIX_HEALTH_PATH"),
        )

    def build_provider(self) -> MatriksRestProvider:
        return MatriksRestProvider(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            endpoints=MatriksEndpointConfig(
                symbols_path=self.symbols_path,
                metadata_path=self.metadata_path,
                history_path=self.history_path,
                latest_path=self.latest_path,
                health_path=self.health_path,
            ),
        )
