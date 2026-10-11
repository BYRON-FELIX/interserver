from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    # Public auth
    path("signup/", views.signup, name="signup"),

    # Logged-in area
    path("dashboard/", views.home, name="home"),
    path("dashboard/services/", views.services, name="services"),
    path(
        "dashboard/services/<int:service_id>/",
        views.service_detail,
        name="service_detail",
    ),
    path(
        "dashboard/services/<int:service_id>/dns/",
        views.dns_editor,
        name="dns_editor",
    ),
    path(
        "dashboard/services/<int:service_id>/dns/add/",
        views.dns_add,
        name="dns_add",
    ),
    path(
        "dashboard/services/<int:service_id>/dns/<int:record_id>/delete/",
        views.dns_delete,
        name="dns_delete",
    ),

    # Public marketing pages
    path("", views.landing, name="landing"),
    path("hosting/", views.hosting, name="hosting"),
    path("vps/", views.vps, name="vps"),
    path("domains/", views.domains, name="domains"),

    # Cart / checkout / billing
    path("cart/", views.view_cart, name="cart"),
    path("cart/add/<int:plan_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:plan_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("checkout/", views.checkout, name="checkout"),
    path("billing/", views.invoice_list, name="invoice_list"),
    path(
        "billing/invoice/<int:invoice_id>/",
        views.invoice_detail,
        name="invoice_detail",
    ),
    path(
        "billing/invoice/<int:invoice_id>/receipt/",
        views.invoice_receipt,
        name="invoice_receipt",
    ),
    path(
        "billing/invoice/<int:invoice_id>/pay/",
        views.pay_invoice,
        name="pay_invoice",
    ),
    path(
        "billing/invoice/<int:invoice_id>/status/",
        views.invoice_payment_status,
        name="invoice_payment_status",
    ),
    path("payments/payhero/callback/", views.payhero_callback, name="payhero_callback"),
]