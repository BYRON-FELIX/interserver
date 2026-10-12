from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .payhero import PayHeroClient


class PayHeroClientTests(SimpleTestCase):
    @override_settings(
        PAYHERO_API_URL="https://payhero.example/api/v2/payments",
        PAYHERO_AUTH_TOKEN="test-token",
        PAYHERO_CHANNEL_ID="13857",
        PAYHERO_PROVIDER="m-pesa",
    )
    @patch("dashboard.payhero.requests.post")
    def test_stk_push_sends_v2_payload_and_authorization_header(self, post):
        response = post.return_value
        response.status_code = 201
        response.json.return_value = {"success": True, "status": "QUEUED"}

        result = PayHeroClient().stk_push(
            amount_kes="3500",
            phone="0712345678",
            reference="INV-2026-0001",
            description="Payment for INV-2026-0001",
            callback_url="https://example.com/payments/payhero/callback/",
        )

        self.assertTrue(result["success"])
        post.assert_called_once_with(
            "https://payhero.example/api/v2/payments",
            json={
                "amount": 3500,
                "phone_number": "254712345678",
                "channel_id": 13857,
                "provider": "m-pesa",
                "external_reference": "INV-2026-0001",
                "callback_url": "https://example.com/payments/payhero/callback/",
            },
            headers={
                "Authorization": "Basic test-token",
                "Content-Type": "application/json",
            },
            timeout=15,
        )

    def test_callback_fields_supports_payhero_v2_callback_shape(self):
        from .views import _callback_fields

        fields = _callback_fields(
            {
                "status": True,
                "response": {
                    "Status": "Success",
                    "ResultCode": 0,
                    "ExternalReference": "INV-2026-0001",
                },
            }
        )

        self.assertEqual(fields["Status"], "Success")
        self.assertEqual(fields["ResultCode"], 0)
        self.assertEqual(fields["ExternalReference"], "INV-2026-0001")
