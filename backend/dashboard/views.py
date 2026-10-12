from decimal import Decimal, ROUND_HALF_UP
import json

from django import forms
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from .cart import (
    Cart,
    DOMAIN_REGISTRATION_PRICE_KES,
    normalize_domain_name,
)
from .currencies import kes_to_usd, usd_to_kes
from .models import (
    Service,
    Invoice,
    ActivityLog,
    Plan,
    Payment,
    UserProfile,
    DNSRecord,
)
from .payhero import PayHeroClient
from .services_fake import (
    default_domain_records,
    provision_domain,
    provision_vps,
)


# Human label + icon key for each Service.Kind — used to build the cards
SERVICE_CARDS = [
    ("webhosting", "Webhosting", "globe"),
    ("vps", "VPS", "server"),
    ("domains", "Domains", "globe"),
    ("storage", "Storage", "folder"),
    ("mail", "Mail", "envelope"),
    ("licenses", "Licenses", "key"),
    ("floating_ip", "Floating IPs", "network"),
    ("scrub_ip", "Scrub IPs", "filter"),
    ("rapid_deploy", "Rapid Deploy Servers", "cloud"),
]


@login_required
def home(request):
    user = request.user

    # --- Prepaid balance (from profile, fallback to 0) -----------------
    profile = getattr(user, "profile", None)
    prepaid_balance = profile.prepaid_balance if profile else 0

    # --- Unpaid invoices -------------------------------------------------
    unpaid_qs = Invoice.objects.filter(owner=user, status=Invoice.Status.UNPAID)
    unpaid_total = unpaid_qs.aggregate(total=Sum("amount"))["total"] or 0
    unpaid_count = unpaid_qs.count()

    # --- Service counts per kind ----------------------------------------
    counts_by_kind = dict(
        Service.objects.filter(owner=user)
        .values_list("kind")
        .annotate(c=Count("id"))
    )

    cards = []
    for kind_key, label, icon in SERVICE_CARDS:
        # Service.Kind enum uses "floating_ip" etc — but our label group
        # for "Domains" is really kind == 'domain'
        lookup_key = kind_key.rstrip("s") if kind_key.endswith("s") and kind_key != "vps" else kind_key
        count = counts_by_kind.get(lookup_key, 0)
        cards.append({
            "key": kind_key,
            "label": label,
            "icon": icon,
            "count": count,
            "active": count > 0,
        })

    # --- Recent activity -------------------------------------------------
    recent_activity = ActivityLog.objects.filter(
        Q(owner=user) | Q(owner__isnull=True)
    )[:12]

    context = {
        "prepaid_balance": prepaid_balance,
        "unpaid_total": unpaid_total,
        "unpaid_count": unpaid_count,
        "cards": cards,
        "recent_activity": recent_activity,
        "profile": profile,
    }
    return render(request, "dashboard/index.html", context)

@login_required
def services(request):
    """
    List all services owned by the logged-in user.
    Supports filtering by ?kind=vps (or any Service.Kind value).
    """
    user = request.user

    kind_filter = request.GET.get("kind", "").strip()

    qs = Service.objects.filter(owner=user)
    if kind_filter in Service.Kind.values:
        qs = qs.filter(kind=kind_filter)

    # Counts per kind for the filter pills
    kind_counts = {"all": Service.objects.filter(owner=user).count()}
    for value, label in Service.Kind.choices:
        kind_counts[value] = Service.objects.filter(
            owner=user, kind=value
        ).count()

    # Build filter pills list with labels
    filters = [{"key": "", "label": "All", "count": kind_counts["all"]}]
    for value, label in Service.Kind.choices:
        filters.append(
            {"key": value, "label": label, "count": kind_counts[value]}
        )

    context = {
        "services": qs,
        "filters": filters,
        "active_filter": kind_filter,
    }
    return render(request, "dashboard/services.html", context)


@login_required
def service_detail(request, service_id):
    """Show an owned service's details and credentials."""
    service = get_object_or_404(
        Service,
        id=service_id,
        owner=request.user,
    )
    template = (
        "dashboard/service_detail_vps.html"
        if service.kind == Service.Kind.VPS
        else (
            "dashboard/service_detail_domain.html"
            if service.kind == Service.Kind.DOMAIN
            else "dashboard/service_detail_generic.html"
        )
    )
    dns_count = (
        service.dns_records.count()
        if service.kind == Service.Kind.DOMAIN
        else 0
    )
    context = {
        "service": service,
        "dns_count": dns_count,
    }
    if service.kind == Service.Kind.DOMAIN:
        context["renewal_price_kes"] = DOMAIN_REGISTRATION_PRICE_KES
    return render(
        request,
        template,
        context,
    )


@login_required
def dns_editor(request, service_id):
    """Show DNS records for a domain service."""
    service = get_object_or_404(
        Service,
        id=service_id,
        owner=request.user,
        kind=Service.Kind.DOMAIN,
    )
    records = service.dns_records.all().order_by("type", "name")
    return render(
        request,
        "dashboard/dns_editor.html",
        {
            "service": service,
            "records": records,
            "record_types": DNSRecord.Type.choices,
        },
    )


@login_required
@require_POST
def dns_add(request, service_id):
    service = get_object_or_404(
        Service,
        id=service_id,
        owner=request.user,
        kind=Service.Kind.DOMAIN,
    )

    record_type = (request.POST.get("type") or "").strip().upper()
    name = (request.POST.get("name") or "").strip()
    value = (request.POST.get("value") or "").strip()
    ttl_raw = (request.POST.get("ttl") or "3600").strip()
    priority_raw = (request.POST.get("priority") or "").strip()

    if record_type not in dict(DNSRecord.Type.choices):
        messages.error(request, "Invalid DNS record type.")
        return redirect("dashboard:dns_editor", service_id=service.id)

    if not name or not value:
        messages.error(request, "Record name and value are required.")
        return redirect("dashboard:dns_editor", service_id=service.id)

    if len(name) > 128 or len(value) > 255:
        messages.error(request, "Record name or value is too long.")
        return redirect("dashboard:dns_editor", service_id=service.id)

    try:
        ttl = int(ttl_raw)
    except ValueError:
        ttl = 0
    if not 60 <= ttl <= 86400:
        messages.error(request, "TTL must be between 60 and 86400 seconds.")
        return redirect("dashboard:dns_editor", service_id=service.id)

    priority = None
    if priority_raw:
        try:
            priority = int(priority_raw)
        except ValueError:
            priority = -1
        if not 0 <= priority <= 65535:
            messages.error(request, "Priority must be between 0 and 65535.")
            return redirect("dashboard:dns_editor", service_id=service.id)
        if record_type not in {DNSRecord.Type.MX, DNSRecord.Type.SRV}:
            messages.error(request, "Priority is only valid for MX and SRV records.")
            return redirect("dashboard:dns_editor", service_id=service.id)

    with transaction.atomic():
        DNSRecord.objects.create(
            service=service,
            type=record_type,
            name=name,
            value=value,
            ttl=ttl,
            priority=priority,
        )
        ActivityLog.objects.create(
            owner=request.user,
            title=f"DNS record added · {record_type} {name}",
            detail=f"{value} (TTL {ttl}) on {service.name}",
            category=ActivityLog.Category.SERVICE,
        )

    messages.success(request, f"{record_type} record for {name} added.")
    return redirect("dashboard:dns_editor", service_id=service.id)


@login_required
@require_POST
def dns_delete(request, service_id, record_id):
    service = get_object_or_404(
        Service,
        id=service_id,
        owner=request.user,
        kind=Service.Kind.DOMAIN,
    )

    with transaction.atomic():
        record = get_object_or_404(
            DNSRecord.objects.select_for_update(),
            id=record_id,
            service=service,
        )

        if record.type == DNSRecord.Type.A:
            a_records = service.dns_records.select_for_update().filter(
                type=DNSRecord.Type.A
            )
            if a_records.count() <= 1:
                messages.error(
                    request,
                    "You can't delete the last A record — the domain would stop resolving.",
                )
                return redirect("dashboard:dns_editor", service_id=service.id)

        label = f"{record.type} {record.name}"
        record.delete()
        ActivityLog.objects.create(
            owner=request.user,
            title=f"DNS record deleted · {label}",
            detail=f"From {service.name}",
            category=ActivityLog.Category.SERVICE,
        )

    messages.info(request, f"{label} record deleted.")
    return redirect("dashboard:dns_editor", service_id=service.id)


# ============================================================
# PUBLIC MARKETING VIEWS
# ============================================================

def landing(request):
    """
    Public homepage — hero, featured plans, trust strip, footer.
    If the user is logged in, still show the marketing page;
    they can click "Dashboard" in the nav.
    """
    featured_hosting = (
        Plan.objects
        .filter(category=Plan.Category.SHARED_HOSTING, is_active=True)
        .order_by("sort_order")[:3]
    )
    featured_vps = (
        Plan.objects
        .filter(category=Plan.Category.VPS, is_active=True)
        .order_by("sort_order")[:3]
    )
    context = {
        "featured_hosting": featured_hosting,
        "featured_vps": featured_vps,
    }
    return render(request, "dashboard/landing.html", context)


def hosting(request):
    """Public page listing all shared hosting + WordPress plans."""
    shared = Plan.objects.filter(
        category=Plan.Category.SHARED_HOSTING, is_active=True
    ).order_by("sort_order")
    wordpress = Plan.objects.filter(
        category=Plan.Category.WORDPRESS, is_active=True
    ).order_by("sort_order")
    context = {
        "shared_plans": shared,
        "wordpress_plans": wordpress,
    }
    return render(request, "dashboard/hosting.html", context)


def vps(request):
    """Public page listing VPS + Dedicated plans."""
    vps_plans = Plan.objects.filter(
        category=Plan.Category.VPS, is_active=True
    ).order_by("sort_order")
    dedicated_plans = Plan.objects.filter(
        category=Plan.Category.DEDICATED, is_active=True
    ).order_by("sort_order")
    context = {
        "vps_plans": vps_plans,
        "dedicated_plans": dedicated_plans,
    }
    return render(request, "dashboard/vps.html", context)


def domains(request):
    """Public domain search + pricing."""
    tlds = Plan.objects.filter(
        category=Plan.Category.DOMAIN, is_active=True
    ).order_by("sort_order")

    query = request.GET.get("domain", "").strip()
    search_result = None

    if query:
        normalized_domain = normalize_domain_name(query)
        if normalized_domain:
            matching_plan = next(
                (
                    plan
                    for plan in sorted(tlds, key=lambda item: len(item.name), reverse=True)
                    if normalized_domain.endswith(plan.name.lower())
                    and normalized_domain[: -len(plan.name)]
                ),
                None,
            )
            matching_plan = matching_plan or next(
                (plan for plan in tlds if plan.name.lower() == ".com"),
                tlds[0] if tlds else None,
            )
            search_result = {
                "query": normalized_domain,
                "available": True,
                "price_kes": DOMAIN_REGISTRATION_PRICE_KES,
                "plan_id": matching_plan.id if matching_plan else None,
            }
        else:
            messages.error(request, "Enter a valid domain name to search.")

    context = {
        "tlds": tlds,
        "search_result": search_result,
        "domain_registration_price_kes": DOMAIN_REGISTRATION_PRICE_KES,
    }
    return render(request, "dashboard/domains.html", context)


# ============================================================
# CART / CHECKOUT
# ============================================================

@require_POST
def add_to_cart(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id, is_active=True)
    cart = Cart(request)
    domain = None
    if plan.category == Plan.Category.DOMAIN:
        domain = normalize_domain_name(request.POST.get("domain", ""))
        if not domain:
            messages.error(request, "Enter a valid domain name to register.")
            return redirect("dashboard:domains")
        cart.add(plan, domain=domain)
        messages.success(request, f"Added “{domain}” to your cart.")
    else:
        cart.add(plan)
        messages.success(request, f"Added “{plan.name}” to your cart.")
    return redirect("dashboard:cart")


def view_cart(request):
    cart = Cart(request)
    return render(request, "dashboard/cart.html", {
        "cart_items": cart.items(),
        "cart_total_kes": cart.total_kes(),
    })


@require_POST
def remove_from_cart(request, plan_id):
    cart = Cart(request)
    cart.remove(plan_id)
    messages.info(request, "Item removed from cart.")
    return redirect("dashboard:cart")


@login_required
def checkout(request):
    """
    Confirms the cart and creates real Invoice + Service rows (pending),
    then redirects to the invoice detail page.

    Plans with trial days charge their setup fee now; plans without a trial
    charge their recurring price. VPS and dedicated servers receive fictional
    provisioning data; domain plans receive nameservers and starter DNS records.
    """
    cart = Cart(request)
    items = cart.items()

    if not items:
        messages.warning(request, "Your cart is empty.")
        return redirect("dashboard:cart")

    if request.method == "POST":
        with transaction.atomic():
            today = timezone.now().date()

            invoice_total_usd = Decimal("0.00")
            non_domain_total_usd = Decimal("0.00")
            domain_total_kes = Decimal("0.00")
            service_specs = []

            for item in items:
                plan = item["plan"]

                if plan.trial_days and plan.trial_days > 0:
                    charge_now = plan.setup_fee
                    renews_on = today + timezone.timedelta(days=plan.trial_days)
                else:
                    renews_on = _renewal_date_for(plan)

                if plan.category == Plan.Category.DOMAIN:
                    domain_charge_kes = (
                        DOMAIN_REGISTRATION_PRICE_KES * item["quantity"]
                    )
                    charge_now = kes_to_usd(domain_charge_kes)
                    domain_total_kes += domain_charge_kes
                    service_price = kes_to_usd(DOMAIN_REGISTRATION_PRICE_KES)
                else:
                    charge_now = (
                        plan.setup_fee
                        if plan.trial_days and plan.trial_days > 0
                        else plan.price * item["quantity"]
                    )
                    non_domain_total_usd += charge_now
                    service_price = plan.price

                invoice_total_usd += charge_now
                service_specs.append({
                    "plan": plan,
                    "renews_on": renews_on,
                    "price": service_price,
                    "domain": item["domain"],
                })

            invoice_total_kes = (
                usd_to_kes(non_domain_total_usd)
                if non_domain_total_usd
                else Decimal("0.00")
            ) + domain_total_kes

            invoice = Invoice.objects.create(
                owner=request.user,
                number=_next_invoice_number(),
                amount=invoice_total_usd,
                kes_amount=invoice_total_kes,
                status=Invoice.Status.UNPAID,
                issued_on=today,
                due_on=today + timezone.timedelta(days=7),
            )

            for spec in service_specs:
                plan = spec["plan"]
                service = Service.objects.create(
                    owner=request.user,
                    invoice=invoice,
                    kind=_service_kind_for_plan(plan),
                    name=spec["domain"] or plan.name,
                    status=Service.Status.PENDING,
                    renews_on=spec["renews_on"],
                    price=spec["price"],
                )

                if plan.category == Plan.Category.VPS:
                    provision_vps(service)
                    service.save()
                elif plan.category == Plan.Category.DEDICATED:
                    provision_vps(service)
                    service.name = f"{plan.name} · dedicated"
                    service.save()
                elif plan.category == Plan.Category.DOMAIN:
                    provision_domain(service)
                    service.save()
                    for record in default_domain_records(service):
                        DNSRecord.objects.create(service=service, **record)

            cart.clear()

            ActivityLog.objects.create(
                owner=request.user,
                title=f"Order placed · Invoice #{invoice.number}",
                detail=f"{len(items)} item(s) · ${invoice_total_usd}",
                category=ActivityLog.Category.BILLING,
            )

        messages.success(
            request,
            "Order placed — please complete payment to activate your services.",
        )
        return redirect("dashboard:invoice_detail", invoice_id=invoice.id)

    return render(request, "dashboard/checkout.html", {
        "cart_items": items,
        "cart_total_kes": cart.total_kes(),
    })


@login_required
def invoice_list(request):
    invoices = Invoice.objects.filter(owner=request.user)
    return render(request, "dashboard/invoice_list.html", {"invoices": invoices})


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, owner=request.user)
    latest_payment = invoice.payments.order_by("-created_at").first()
    return render(request, "dashboard/invoice_detail.html", {
        "invoice": invoice,
        "latest_payment": latest_payment,
    })


@login_required
def invoice_receipt(request, invoice_id):
    """Show a printable receipt for a paid invoice."""
    invoice = get_object_or_404(Invoice, id=invoice_id, owner=request.user)
    if invoice.status != Invoice.Status.PAID:
        messages.warning(request, "Receipts are only available for paid invoices.")
        return redirect("dashboard:invoice_detail", invoice_id=invoice.id)

    payment = invoice.payments.filter(
        status=Payment.Status.SUCCESS
    ).order_by("-created_at").first()
    return render(
        request,
        "dashboard/invoice_receipt.html",
        {
            "invoice": invoice,
            "payment": payment,
        },
    )


def _next_invoice_number():
    year = timezone.now().year
    last = Invoice.objects.filter(
        number__startswith=f"INV-{year}-"
    ).order_by("-id").first()
    if last:
        try:
            sequence = int(last.number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1
    return f"INV-{year}-{sequence:04d}"


def _service_kind_for_plan(plan):
    mapping = {
        Plan.Category.SHARED_HOSTING: Service.Kind.WEBHOSTING,
        Plan.Category.WORDPRESS: Service.Kind.WEBHOSTING,
        Plan.Category.VPS: Service.Kind.VPS,
        Plan.Category.DEDICATED: Service.Kind.VPS,
        Plan.Category.DOMAIN: Service.Kind.DOMAIN,
    }
    return mapping.get(plan.category, Service.Kind.WEBHOSTING)


def _renewal_date_for(plan):
    today = timezone.now().date()
    if plan.billing_period == Plan.BillingPeriod.YEARLY:
        return today + timezone.timedelta(days=365)
    if plan.billing_period == Plan.BillingPeriod.MONTHLY:
        return today + timezone.timedelta(days=30)
    return None


# ============================================================
# PAYMENTS (PayHero / M-Pesa)
# ============================================================

@login_required
@require_POST
def pay_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, owner=request.user)

    if invoice.status != Invoice.Status.UNPAID:
        messages.info(request, "This invoice is already paid or void.")
        return redirect("dashboard:invoice_detail", invoice_id=invoice.id)

    phone = (request.POST.get("phone") or "").strip()
    if not phone:
        messages.error(request, "Please enter your M-Pesa phone number.")
        return redirect("dashboard:invoice_detail", invoice_id=invoice.id)

    amount_kes = (invoice.kes_amount or usd_to_kes(invoice.amount)).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    )
    normalized_phone = PayHeroClient.normalize_phone(phone)

    with transaction.atomic():
        invoice.kes_amount = amount_kes
        invoice.save(update_fields=["kes_amount"])
        payment = Payment.objects.create(
            invoice=invoice,
            amount_kes=amount_kes,
            phone=normalized_phone,
            reference=invoice.number,
            status=Payment.Status.INITIATED,
        )

    callback_url = (
        getattr(settings, "PAYHERO_CALLBACK_URL", "")
        or request.build_absolute_uri(reverse("dashboard:payhero_callback"))
    )

    result = PayHeroClient().stk_push(
        amount_kes=amount_kes,
        phone=phone,
        reference=invoice.number,
        description=f"Payment for {invoice.number}",
        callback_url=callback_url,
    )

    payment.request_payload = {
        "amount_kes": str(amount_kes),
        "phone": normalized_phone,
        "reference": invoice.number,
    }
    raw_response = result.get("raw")
    payment.response_payload = raw_response if isinstance(raw_response, dict) else {}

    if result.get("success"):
        payment.status = Payment.Status.PENDING
        payment.save()
        messages.success(
            request,
            "STK push sent. Check your phone and enter your M-Pesa PIN to complete payment.",
        )
    else:
        payment.status = Payment.Status.FAILED
        payment.error_message = (result.get("error") or "Unknown error")[:255]
        payment.save()
        messages.error(
            request,
            f"Payment failed to start: {payment.error_message}",
        )

    return redirect("dashboard:invoice_detail", invoice_id=invoice.id)


@login_required
def invoice_payment_status(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, owner=request.user)
    latest_payment = invoice.payments.order_by("-created_at").first()
    return JsonResponse({
        "invoice_status": invoice.status,
        "invoice_paid": invoice.status == Invoice.Status.PAID,
        "payment_status": latest_payment.status if latest_payment else None,
        "payment_error": latest_payment.error_message if latest_payment else "",
    })


def _callback_fields(payload):
    if not isinstance(payload, dict):
        return {}
    merged = dict(payload)
    response = payload.get("response")
    if isinstance(response, dict):
        merged.update(response)
    body = payload.get("Body")
    if isinstance(body, dict):
        callback = body.get("stkCallback")
        if isinstance(callback, dict):
            merged.update(callback)
            callback_metadata = callback.get("CallbackMetadata")
            if isinstance(callback_metadata, dict):
                values = callback_metadata.get("Item", [])
                if isinstance(values, list):
                    for item in values:
                        if isinstance(item, dict) and "Name" in item:
                            merged.setdefault(str(item["Name"]), item.get("Value"))
            return merged
    return merged


@csrf_exempt
@require_POST
def payhero_callback(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"received": False, "error": "Invalid JSON"}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"received": False, "error": "Expected a JSON object"}, status=400)

    fields = _callback_fields(payload)
    reference = next(
        (
            fields.get(key)
            for key in (
                "ExternalReference",
                "external_reference",
                "reference",
                "invoice",
            )
            if fields.get(key) not in (None, "")
        ),
        "",
    )
    status_raw = next(
        (
            fields.get(key)
            for key in (
                "ResultCode",
                "Status",
                "transaction_status",
                "status",
            )
            if fields.get(key) not in (None, "")
        ),
        "",
    )
    status_string = str(status_raw).lower()
    success = status_string in {"success", "successful", "0", "completed", "paid"}

    payment = None
    if reference:
        payment = Payment.objects.filter(
            reference=reference,
        ).order_by("-created_at").first()
    if payment is None:
        return JsonResponse({"received": False, "error": "Payment reference not found"}, status=404)

    with transaction.atomic():
        payment.callback_payload = payload
        if success:
            payment.status = Payment.Status.SUCCESS
            payment.error_message = ""
            payment.save()

            invoice = payment.invoice
            if invoice.status != Invoice.Status.PAID:
                invoice.status = Invoice.Status.PAID
                invoice.paid_on = timezone.now().date()
                invoice.save(update_fields=["status", "paid_on"])

                Service.objects.filter(
                    invoice=invoice,
                    status=Service.Status.PENDING,
                ).update(status=Service.Status.ACTIVE)

                ActivityLog.objects.create(
                    owner=invoice.owner,
                    title=f"Payment received · {invoice.number}",
                    detail=f"KSh {payment.amount_kes} · {payment.phone}",
                    category=ActivityLog.Category.BILLING,
                )
        elif status_string not in {"", "pending", "initiated", "processing"}:
            if status_string in {"cancelled", "canceled"}:
                payment.status = Payment.Status.CANCELLED
            elif status_string == "timeout":
                payment.status = Payment.Status.TIMEOUT
            else:
                payment.status = Payment.Status.FAILED
            payment.error_message = str(
                fields.get("message") or fields.get("ResultDesc") or ""
            )[:255]
            payment.save()
        else:
            payment.save(update_fields=["callback_payload", "updated_at"])

    return JsonResponse({"received": True})


# ============================================================
# PUBLIC AUTH — SIGN UP
# ============================================================

class SignUpForm(UserCreationForm):
    """User creation form with a required email and optional full name."""

    email = forms.EmailField(required=True)
    full_name = forms.CharField(required=False, max_length=150)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    field_order = ["username", "email", "full_name", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        full_name = self.cleaned_data.get("full_name", "").strip()
        if full_name:
            first_name, _, last_name = full_name.partition(" ")
            user.first_name = first_name
            user.last_name = last_name
        if commit:
            user.save()
        return user


def signup(request):
    """Create a user and profile, then sign the user in."""
    if request.user.is_authenticated:
        return redirect("dashboard:home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                UserProfile.objects.create(user=user)
                ActivityLog.objects.create(
                    owner=user,
                    title="Account created",
                    detail=f"Welcome, {user.username}",
                    category=ActivityLog.Category.SYSTEM,
                )
            auth_login(request, user)
            messages.success(request, "Welcome to InterServer!")
            return redirect("dashboard:home")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})