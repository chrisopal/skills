from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from ..errors import UnsupportedFeatureError


@dataclass(frozen=True)
class ReferenceImage:
    data: bytes
    mime_type: str = "image/png"


@dataclass(frozen=True)
class ImageRenderRequest:
    prompt: str
    model: str
    resolution: str = "3840x2160"
    aspect_ratio: str = "16:9"
    mime_type: str = "image/png"
    seed: int | None = None
    reference_images: Sequence[ReferenceImage] | None = None


class ImageProvider(ABC):
    supports_reference_images: bool = False
    supports_seed: bool = False

    @abstractmethod
    def render(self, request: ImageRenderRequest) -> bytes:
        """Render an image and return the raw bytes."""

    @property
    def capability_info(self) -> dict[str, bool]:
        return {
            "supports_reference_images": self.supports_reference_images,
            "supports_seed": self.supports_seed,
        }

    def _validate_request(self, request: ImageRenderRequest) -> None:
        if request.seed is not None and not self.supports_seed:
            raise UnsupportedFeatureError("This image provider does not support seed")
        if request.reference_images and not self.supports_reference_images:
            raise UnsupportedFeatureError("This image provider does not support reference images")

    def close(self) -> None:
        """Hook for providers that hold network clients."""
