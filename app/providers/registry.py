"""Registry for authorised odds-provider adapters.

The registry deliberately knows nothing about a provider's credentials or
commercial entitlements. Only explicitly configured adapters are registered.
"""
from typing import Iterable

from app.providers.base import OddsProvider


class ProviderRegistry:
    """In-process registry of provider adapters keyed by stable provider ID."""

    def __init__(self, providers: Iterable[OddsProvider] = ()) -> None:
        self._providers: dict[str, OddsProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: OddsProvider) -> None:
        provider_id = getattr(provider, "provider_id", None)
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("provider must define a non-empty provider_id")
        key = provider_id.strip().lower()
        if key in self._providers:
            raise ValueError(f"provider already registered: {key}")
        self._providers[key] = provider

    def get(self, provider_id: str) -> OddsProvider:
        key = provider_id.strip().lower()
        try:
            return self._providers[key]
        except KeyError as exc:
            raise KeyError(f"provider is not registered: {key}") from exc

    def list_provider_ids(self) -> list[str]:
        return sorted(self._providers)

    def __len__(self) -> int:
        return len(self._providers)
