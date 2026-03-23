from __future__ import annotations

import unittest

import httpx

from app.providers.base import ProviderDiscoveryError
from app.providers.openrouter_discovery import OpenRouterModelDiscoveryClient


class OpenRouterModelDiscoveryClientTests(unittest.TestCase):
    def test_list_models_returns_normalized_models(self) -> None:
        client = OpenRouterModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/api/v1",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200,
                        json={
                            "data": [
                                {
                                    "id": "openai/gpt-5.4-mini",
                                    "canonical_slug": "openai/gpt-5.4-mini-20260317",
                                    "created": 1773748178,
                                }
                            ]
                        },
                    )
                )
            ),
        )

        models = client.list_models()

        self.assertEqual(len(models), 1)
        self.assertEqual(models[0].provider, "openrouter")
        self.assertEqual(models[0].external_model_id, "openai/gpt-5.4-mini")
        self.assertEqual(models[0].owned_by, "openai/gpt-5.4-mini-20260317")
        self.assertEqual(models[0].created_at_unix, 1773748178)

    def test_list_models_raises_on_http_error(self) -> None:
        client = OpenRouterModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/api/v1",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(429, json={"error": "rate limited"})
                )
            ),
        )

        with self.assertRaises(ProviderDiscoveryError) as ctx:
            client.list_models()

        self.assertIn("status 429", str(ctx.exception))

    def test_list_models_raises_when_payload_has_no_data_list(self) -> None:
        client = OpenRouterModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/api/v1",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, json={"object": "list"})
                )
            ),
        )

        with self.assertRaises(ProviderDiscoveryError) as ctx:
            client.list_models()

        self.assertIn("missing 'data' list", str(ctx.exception))

    def test_list_models_raises_when_item_has_no_id(self) -> None:
        client = OpenRouterModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/api/v1",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200,
                        json={"data": [{"canonical_slug": "openai/gpt-5.4-mini-20260317"}]},
                    )
                )
            ),
        )

        with self.assertRaises(ProviderDiscoveryError) as ctx:
            client.list_models()

        self.assertIn("missing valid 'id'", str(ctx.exception))

    def test_list_models_raises_when_api_key_is_missing(self) -> None:
        client = OpenRouterModelDiscoveryClient(
            api_key="",
            base_url="https://example.test/api/v1",
        )

        with self.assertRaises(ProviderDiscoveryError) as ctx:
            client.list_models()

        self.assertIn("OPENROUTER_API_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
