from __future__ import annotations

import unittest

import httpx

from app.providers.base import ProviderDiscoveryError
from app.providers.openai_discovery import OpenAIModelDiscoveryClient


class OpenAIModelDiscoveryClientTests(unittest.TestCase):
    def test_list_models_returns_normalized_models(self) -> None:
        client = OpenAIModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/v1",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200,
                        json={
                            "data": [
                                {
                                    "id": "gpt-5-mini",
                                    "owned_by": "openai",
                                    "created": 1735689600,
                                }
                            ]
                        },
                    )
                )
            ),
        )

        models = client.list_models()

        self.assertEqual(len(models), 1)
        self.assertEqual(models[0].provider, "openai")
        self.assertEqual(models[0].external_model_id, "gpt-5-mini")
        self.assertEqual(models[0].owned_by, "openai")
        self.assertEqual(models[0].created_at_unix, 1735689600)

    def test_list_models_raises_on_http_error(self) -> None:
        client = OpenAIModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/v1",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(401, json={"error": "unauthorized"})
                )
            ),
        )

        with self.assertRaises(ProviderDiscoveryError) as ctx:
            client.list_models()

        self.assertIn("status 401", str(ctx.exception))

    def test_list_models_raises_when_payload_has_no_data_list(self) -> None:
        client = OpenAIModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/v1",
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
        client = OpenAIModelDiscoveryClient(
            api_key="test-key",
            base_url="https://example.test/v1",
            client=httpx.Client(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(
                        200,
                        json={"data": [{"owned_by": "openai", "created": 1735689600}]},
                    )
                )
            ),
        )

        with self.assertRaises(ProviderDiscoveryError) as ctx:
            client.list_models()

        self.assertIn("missing valid 'id'", str(ctx.exception))

    def test_list_models_raises_when_api_key_is_missing(self) -> None:
        client = OpenAIModelDiscoveryClient(
            api_key="",
            base_url="https://example.test/v1",
        )

        with self.assertRaises(ProviderDiscoveryError) as ctx:
            client.list_models()

        self.assertIn("OPENAI_API_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
