from __future__ import annotations

import unittest

from piserver.core.access_control import (
    configured_access_token,
    is_loopback_address,
    same_origin,
    select_bind_host,
    valid_bearer_token,
)


class AccessPolicyTests(unittest.TestCase):
    def test_default_is_localhost_only(self):
        self.assertEqual(select_bind_host({}), "127.0.0.1")
        self.assertEqual(select_bind_host({"PISERVER_HOST": "localhost"}), "localhost")
        self.assertEqual(select_bind_host({"PISERVER_HOST": "::1"}), "::1")

    def test_remote_bind_without_token_fails(self):
        for host in ("0.0.0.0", "192.168.1.10", "::", "hostname"):
            with self.subTest(host=host), self.assertRaises(RuntimeError):
                select_bind_host({"PISERVER_HOST": host})

    def test_long_token_enables_lan_and_is_required(self):
        token = "x" * 32
        self.assertEqual(configured_access_token({"PISERVER_ACCESS_TOKEN": token}), token)
        self.assertEqual(select_bind_host({"PISERVER_ACCESS_TOKEN": token}), "0.0.0.0")
        self.assertEqual(select_bind_host({"PISERVER_ACCESS_TOKEN": token, "PISERVER_HOST": "192.168.1.5"}), "192.168.1.5")
        with self.assertRaisesRegex(RuntimeError, "32 characters"):
            configured_access_token({"PISERVER_ACCESS_TOKEN": "short"})

    def test_loopback_address_validation(self):
        self.assertTrue(is_loopback_address("127.0.0.1"))
        self.assertTrue(is_loopback_address("::1"))
        for item in ("", None, "192.168.1.1", "localhost", "0.0.0.0", "::"):
            self.assertFalse(is_loopback_address(item))

    def test_bearer_requires_exact_token(self):
        token = "a" * 32
        self.assertTrue(valid_bearer_token("Bearer " + token, token))
        for header in (None, "", "Bearer a", "bearer " + token, "Basic " + token, "Bearer " + token + "x"):
            self.assertFalse(valid_bearer_token(header, token))
        self.assertFalse(valid_bearer_token("Bearer " + token, ""))

    def test_origin_check_requires_exact_match_when_present(self):
        expected = "http://raspberrypi.local:5000"
        self.assertTrue(same_origin(None, expected))
        self.assertTrue(same_origin(expected, expected))
        self.assertFalse(same_origin("https://attacker.example", expected))
        self.assertFalse(same_origin("null", expected))
        self.assertFalse(same_origin(expected + ".attacker.example", expected))


if __name__ == "__main__":
    unittest.main()
