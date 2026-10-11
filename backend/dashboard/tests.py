from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .payhero import PayHeroClient


class PayHeroClientTests(SimpleTestCase):
    @override_settings(
        PAYHERO_API_URL="https://payhero.example/api/v2/payments/initiate-stk-push",
        PAYHERO_BASIC_AUTH="Basic test-token",
        PAYHERO_CHANNEL_ID="channel-123",
    )
    @patch("dashboard.payhero.requests.post")
    def test_stk_push_sends_v2_payload_and_callback_url(self, post):
        response = post.return_value
        response.status_code = 201
        response.json.return_value = {"success": True, "status": "QUEUED"}
        callback_url = "https://example.com/payments/payhero/callback/"

        result = PayHeroClient().stk_push(
            amount_kes="3500",
            phone="0712345678",
            reference="INV-2026-0001",
            description="Payment for INV-2026-0001",
            callback_url=callback_url,
        )

        self.assertTrue(result["success"])
        post.assert_called_once_with(
            "https://payhero.example/api/v2/payments/initiate-stk-push",
            json={
                "amount": 3500,
                "phone_number": "254712345678",
                "channel_id": "channel-123",
                "provider": "m-pesa",
                "external_reference": "INV-2026-0001",
                "callback_url": callback_url,
            },
            headers={
                "Authorization": "Basic test-token",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
