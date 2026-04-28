from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ImageRenderRequest:
    prompt: str
    model: str
    resolution: str = "3840x2160"
    aspect_ratio: str = "16:9"
    mime_type: str = "image/png"


class ImageProvider(ABC):
    @abstractmethod
    def render(self, request: ImageRenderRequest) -> bytes:
        """Render an image and return the raw bytes."""

    def close(self) -> None:
        """Hook for providers that hold network clients."""
