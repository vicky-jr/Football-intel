from app.providers.registry import ProviderRegistry


class DummyProvider:
    provider_id = "ExampleBook"


def test_registry_registers_and_resolves_provider_case_insensitively():
    provider = DummyProvider()
    registry = ProviderRegistry([provider])
    assert registry.get("examplebook") is provider
    assert registry.list_provider_ids() == ["examplebook"]


def test_registry_rejects_duplicate_provider_ids():
    registry = ProviderRegistry([DummyProvider()])
    try:
        registry.register(DummyProvider())
    except ValueError as exc:
        assert "already registered" in str(exc)
    else:
        raise AssertionError("duplicate provider should be rejected")


def test_registry_rejects_missing_provider_id():
    class InvalidProvider:
        provider_id = ""

    try:
        ProviderRegistry([InvalidProvider()])
    except ValueError as exc:
        assert "provider_id" in str(exc)
    else:
        raise AssertionError("missing provider ID should be rejected")
