from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings

from .models import Invoice, Plan, Service
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


class DomainStoreTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            category=Plan.Category.DOMAIN,
            name=".com",
            slug="test-domain-com",
            tagline="Domain registration",
            price="10.99",
            billing_period=Plan.BillingPeriod.YEARLY,
        )

    def test_every_search_is_shown_as_available_at_kes_1500(self):
        for query in ("taken.com", "ab", "brand-name.co.ke"):
            with self.subTest(query=query):
                response = self.client.get("/domains/", {"domain": query})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Available")
                self.assertContains(response, "KSh 1500 / year")

    def test_domain_checkout_locks_kes_1500_registration_price(self):
        user = User.objects.create_user(
            username="domain-customer",
            password="test-password",
        )
        self.client.force_login(user)
        session = self.client.session
        session["cart"] = {
            str(self.plan.id): {"quantity": 1, "period": "yearly"}
        }
        session.save()

        with patch("dashboard.views.kes_to_usd", return_value=Decimal("11.54")):
            response = self.client.post("/checkout/")

        self.assertEqual(response.status_code, 302)
        invoice = Invoice.objects.get(owner=user)
        self.assertEqual(invoice.kes_amount, Decimal("1500.00"))
        self.assertEqual(invoice.amount, Decimal("11.54"))

    def test_register_button_runs_domain_through_checkout_to_payment(self):
        user = User.objects.create_user(
            username="domain-flow-customer",
            password="test-password",
        )
        self.client.force_login(user)

        search_response = self.client.get("/domains/", {"domain": "example.co.ke"})
        self.assertContains(search_response, "name=\"domain\" value=\"example.co.ke\"")
        self.assertContains(
            search_response,
            f'action="/cart/add/{self.plan.id}/"',
        )

        add_response = self.client.post(
            f"/cart/add/{self.plan.id}/",
            {"domain": "example.co.ke"},
        )
        self.assertRedirects(add_response, "/cart/")
        cart_response = self.client.get("/cart/")
        self.assertContains(cart_response, "example.co.ke")
        self.assertContains(cart_response, "KSh 1500.00")

        with patch("dashboard.views.kes_to_usd", return_value=Decimal("11.54")):
            checkout_response = self.client.post("/checkout/")
        invoice = Invoice.objects.get(owner=user)
        service = Service.objects.get(invoice=invoice)
        self.assertEqual(checkout_response.url, f"/billing/invoice/{invoice.id}/")
        self.assertEqual(service.name, "example.co.ke")
        self.assertContains(
            self.client.get(checkout_response.url),
            f"/billing/invoice/{invoice.id}/pay/",
        )

        with patch(
            "dashboard.views.PayHeroClient.stk_push",
            return_value={"success": True},
        ) as stk_push:
            pay_response = self.client.post(
                f"/billing/invoice/{invoice.id}/pay/",
                {"phone": "0712345678"},
            )
        self.assertEqual(pay_response.status_code, 302)
        stk_push.assert_called_once()
