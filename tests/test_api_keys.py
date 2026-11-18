import os
import json
import secrets
import tempfile
import unittest
from unittest.mock import patch

import httpx

import main
from API.keys import keys_path, lookup_key


class ApiKeyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"LEOAI_KEYS_FILE": os.path.join(self.directory.name, "keys.json")})
        self.env.start()
        main.limiter.reset()
        self.forward = patch("main.forward_openai_request", return_value={"choices": []})
        self.mock_forward = self.forward.start()
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.forward.stop()
        self.env.stop()
        self.directory.cleanup()

    async def post(self, key=None):
        headers = {"Authorization": f"Bearer {key}"} if key else {}
        return await self.client.post("/api/v1/chat/completions", json={"messages": []}, headers=headers)

    async def test_free_access_without_database_and_limit(self):
        for _ in range(10):
            self.assertEqual((await self.post()).status_code, 200)
        self.assertEqual((await self.post()).status_code, 429)
        self.assertEqual(self.mock_forward.call_count, 10)

    async def test_higher_limit_and_independent_keys(self):
        first, second = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        keys_path().write_text(json.dumps({"keys": [first, second]}))
        for _ in range(main.KEY_RPM):
            self.assertEqual((await self.post(first)).status_code, 200)
        self.assertEqual((await self.post(first)).status_code, 429)
        self.assertEqual((await self.post(second)).status_code, 200)
        self.assertEqual((await self.post()).status_code, 200)

    async def test_invalid_and_revoked_keys_never_forward(self):
        self.assertEqual((await self.post("invalid")).status_code, 401)
        key = secrets.token_urlsafe(32)
        keys_path().write_text(json.dumps({"keys": [key]}))
        self.assertIsNotNone(lookup_key(key))
        keys_path().write_text(json.dumps({"keys": []}))
        self.assertIsNone(lookup_key(key))
        self.assertEqual((await self.post(key)).status_code, 401)
        self.mock_forward.assert_not_called()

    async def test_same_key_shares_limit_across_ips(self):
        key = secrets.token_urlsafe(32)
        keys_path().write_text(json.dumps({"keys": [key]}))
        headers = {"Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app, client=("192.0.2.1", 1234)),
            base_url="http://test",
        ) as first, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app, client=("192.0.2.2", 1234)),
            base_url="http://test",
        ) as second:
            for index in range(main.KEY_RPM):
                client = first if index % 2 == 0 else second
                response = await client.post("/api/v1/chat/completions", json={}, headers=headers)
                self.assertEqual(response.status_code, 200)
            for client in (first, second):
                response = await client.post("/api/v1/chat/completions", json={}, headers=headers)
                self.assertEqual(response.status_code, 429)
                # Authenticated requests do not also consume the IP's free quota.
                for _ in range(10):
                    response = await client.post("/api/v1/chat/completions", json={})
                    self.assertEqual(response.status_code, 200)
                response = await client.post("/api/v1/chat/completions", json={})
                self.assertEqual(response.status_code, 429)

    async def test_bad_configuration_fails_closed_but_free_access_works(self):
        for value in ['{', '[]', '{"keys": "bad"}', '{"keys": [123]}', '{"keys": ["short"]}']:
            keys_path().write_text(value)
            self.assertEqual((await self.post("invalid")).status_code, 503)
            self.assertEqual((await self.post()).status_code, 200)

    async def test_private_file_not_served(self):
        keys_path().write_text(json.dumps({"keys": [secrets.token_urlsafe(32)]}))
        self.assertEqual((await self.client.get("/API/keys.json")).status_code, 404)

    async def test_malformed_auth_and_privacy(self):
        for value in ["", "Basic abc", "Bearer", "Bearer ", "Bearer " + "a" * 257]:
            response = await self.client.post("/api/v1/chat/completions", json={}, headers={"Authorization": value})
            self.assertEqual(response.status_code, 401)
        self.assertIn("Optional API keys", (await self.client.get("/privacy")).text)
        self.mock_forward.assert_not_called()


if __name__ == "__main__":
    unittest.main()
