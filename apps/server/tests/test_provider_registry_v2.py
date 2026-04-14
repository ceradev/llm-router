import pytest
from packages.infrastructure.providers.registry import build_provider_clients
from packages.infrastructure.providers.demo_provider import DemoProviderClient
from packages.infrastructure.providers.http_provider_client import HttpProviderClient

class MockSettings:
    openai_api_key = "sk-..."
    anthropic_api_key = None
    groq_api_key = None
    openrouter_api_key = None
    deepseek_api_key = None

def test_build_provider_clients() -> None:
    clients = build_provider_clients(MockSettings())
    assert isinstance(clients["openai"], HttpProviderClient)
    assert isinstance(clients["anthropic"], DemoProviderClient)
