from django.conf import settings
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """
    Extra fields attached to Django's built-in User.
    Access via  request.user.profile
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=32, blank=True)
    company = models.CharField(max_length=128, blank=True)
    customer_since = models.DateField(default=timezone.now)
    prepaid_balance = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    def __str__(self):
        return f"{self.user.username} profile"


class Service(models.Model):
    """
    A single service the customer owns (web hosting, VPS, domain, etc.)
    """

    class Kind(models.TextChoices):
        WEBHOSTING = "webhosting", "Web Hosting"
        VPS = "vps", "VPS"
        DOMAIN = "domain", "Domain"
        STORAGE = "storage", "Storage"
        MAIL = "mail", "Mail"
        LICENSE = "license", "License"
        FLOATING_IP = "floating_ip", "Floating IP"
        SCRUB_IP = "scrub_ip", "Scrub IP"
        RAPID_DEPLOY = "rapid_deploy", "Rapid Deploy Server"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        SUSPENDED = "suspended", "Suspended"
        EXPIRED = "expired", "Expired"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="services",
    )
    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.SET_NULL,
        related_name="services",
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    name = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    renews_on = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    ipv6_address = models.GenericIPAddressField(
        protocol="IPv6", null=True, blank=True
    )
    hostname = models.CharField(max_length=128, blank=True)
    root_username = models.CharField(max_length=32, blank=True, default="root")
    root_password_encrypted = models.CharField(
        max_length=255,
        blank=True,
        help_text="Fernet-encrypted root password. Never store plaintext here.",
    )
    operating_system = models.CharField(max_length=64, blank=True)
    region = models.CharField(max_length=32, blank=True)
    provisioned_at = models.DateTimeField(null=True, blank=True)
    nameservers = models.JSONField(
        default=list,
        blank=True,
        help_text="List of nameserver hostnames (for domain services).",
    )

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"

    @property
    def root_password(self):
        """Decrypt and return the root password."""
        from .credentials import decrypt_secret

        return decrypt_secret(self.root_password_encrypted)

    def set_root_password(self, plaintext: str):
        """Encrypt and store the root password."""
        from .credentials import encrypt_secret

        self.root_password_encrypted = encrypt_secret(plaintext)


class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        VOID = "void", "Void"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invoices",
    )
    number = models.CharField(max_length=32, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    kes_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Locked KES amount at payment time (filled when payment starts).",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.UNPAID
    )
    issued_on = models.DateField(default=timezone.now)
    due_on = models.DateField(null=True, blank=True)
    paid_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_on"]

    def __str__(self):
        return f"INV-{self.number} ({self.get_status_display()})"


class ActivityLog(models.Model):
    """
    Recent-activity feed shown on the dashboard.
    """

    class Category(models.TextChoices):
        SECURITY = "security", "Security"
        BILLING = "billing", "Billing"
        SERVICE = "service", "Service"
        SYSTEM = "system", "System"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activity",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=128)
    detail = models.CharField(max_length=255, blank=True)
    category = models.CharField(
        max_length=16, choices=Category.choices, default=Category.SYSTEM
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "activity logs"

    def __str__(self):
        return self.title


class Plan(models.Model):
    """
    A product you sell. One row = one card on /hosting/ or /vps/ etc.
    """

    class Category(models.TextChoices):
        SHARED_HOSTING = "shared_hosting", "Shared Hosting"
        WORDPRESS = "wordpress", "WordPress Hosting"
        VPS = "vps", "VPS"
        DEDICATED = "dedicated", "Dedicated Server"
        DOMAIN = "domain", "Domain"

    class BillingPeriod(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"
        ONE_TIME = "one_time", "One-time"

    category = models.CharField(max_length=32, choices=Category.choices)
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=140, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period = models.CharField(
        max_length=16,
        choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY,
    )
    setup_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    trial_days = models.PositiveIntegerField(
        default=0,
        help_text="Days before the first recurring charge (0 = charge immediately).",
    )

    # Display specs — stored as JSON-ish text so any category can use them
    # Example: {"storage": "50 GB SSD", "bandwidth": "Unmetered",
    #           "websites": "1", "email_accounts": "10"}
    specs = models.JSONField(default=dict, blank=True)

    # Bullet-list features shown on the plan card
    features = models.JSONField(default=list, blank=True)

    is_featured = models.BooleanField(
        default=False,
        help_text="Highlight this plan on the category page.",
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "sort_order", "price"]

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class Payment(models.Model):
    """
    One record per payment attempt. Populated when an STK push is initiated
    and updated when the PayHero callback arrives.
    """

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        TIMEOUT = "timeout", "Timeout"

    class Provider(models.TextChoices):
        PAYHERO = "payhero", "PayHero (M-Pesa)"

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    provider = models.CharField(
        max_length=16,
        choices=Provider.choices,
        default=Provider.PAYHERO,
    )
    amount_kes = models.DecimalField(max_digits=12, decimal_places=2)
    phone = models.CharField(max_length=20)
    reference = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.INITIATED,
    )
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    callback_payload = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} · {self.amount_kes} KES · {self.get_status_display()}"


class DNSRecord(models.Model):
    """
    A single DNS record inside a domain Service's zone.
    Stored in our DB; not actually propagated to the internet.
    """

    class Type(models.TextChoices):
        A = "A", "A"
        AAAA = "AAAA", "AAAA"
        CNAME = "CNAME", "CNAME"
        MX = "MX", "MX"
        TXT = "TXT", "TXT"
        NS = "NS", "NS"
        SRV = "SRV", "SRV"
        CAA = "CAA", "CAA"

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="dns_records",
    )
    type = models.CharField(max_length=8, choices=Type.choices, default=Type.A)
    name = models.CharField(
        max_length=128,
        help_text="Use @ for the root domain, or a subdomain like 'www'.",
    )
    value = models.CharField(max_length=255)
    ttl = models.PositiveIntegerField(default=3600)
    priority = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Only used for MX and SRV records.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["type", "name"]

    def __str__(self):
        return f"{self.name} {self.type} → {self.value}"