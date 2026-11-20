import unittest

from weread2notionpro.gateway_policy import (
    WEREAD_SKILL_VERSION,
    validate_gateway_response,
)


class GatewayPolicyTests(unittest.TestCase):
    def test_uses_official_skill_version(self):
        self.assertEqual(WEREAD_SKILL_VERSION, "1.0.6")

    def test_upgrade_notice_keeps_successful_business_data_usable(self):
        data = {
            "errcode": 0,
            "books": [{"bookId": "123"}],
            "upgrade_info": {
                "current_version": "1.0.6",
                "latest_version": "1.0.7",
            },
        }

        warning = validate_gateway_response("/shelf/sync", data)

        self.assertIn("non-blocking", warning)
        self.assertIn("current=1.0.6", warning)
        self.assertEqual(data["books"][0]["bookId"], "123")

    def test_error_response_still_fails(self):
        with self.assertRaisesRegex(RuntimeError, "code=-1"):
            validate_gateway_response("/shelf/sync", {"errcode": -1})

    def test_non_mapping_response_fails(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            validate_gateway_response("/shelf/sync", [])


if __name__ == "__main__":
    unittest.main()
