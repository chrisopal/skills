from __future__ import annotations


class ProviderError(RuntimeError):
    """Raised when a provider call fails or returns an unusable payload."""


class UnsupportedFeatureError(RuntimeError):
    """Raised when a provider, capability, or required credential is unavailable."""
