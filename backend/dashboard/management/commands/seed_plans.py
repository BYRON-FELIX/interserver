from decimal import Decimal
from django.core.management.base import BaseCommand
from dashboard.models import Plan


PLANS = [
    # ---------------------------------------------------------
    # SHARED HOSTING
    # ---------------------------------------------------------
    {
        "category": "shared_hosting",
        "name": "Starter",
        "slug": "starter-hosting",
        "tagline": "Perfect for your first website.",
        "price": Decimal("2.50"),
        "billing_period": "monthly",
        "specs": {
            "storage": "30 GB SSD",
            "bandwidth": "Unmetered",
            "websites": "1",
            "email_accounts": "10",
            "databases": "2",
        },
        "features": [
            "Free SSL certificate",
            "1-click WordPress install",
            "cPanel control panel",
            "24/7 support",
        ],
        "sort_order": 1,
    },
    {
        "category": "shared_hosting",
        "name": "Standard",
        "slug": "standard-hosting",
        "tagline": "Best for growing sites and small businesses.",
        "price": Decimal("5.00"),
        "billing_period": "monthly",
        "specs": {
            "storage": "100 GB SSD",
            "bandwidth": "Unmetered",
            "websites": "Unlimited",
            "email_accounts": "Unlimited",
            "databases": "Unlimited",
        },
        "features": [
            "Free SSL certificate",
            "Unlimited email accounts",
            "Free daily backups",
            "Free domain for 1 year",
            "Priority support",
        ],
        "is_featured": True,
        "sort_order": 2,
    },
    {
        "category": "shared_hosting",
        "name": "Business",
        "slug": "business-hosting",
        "tagline": "For high-traffic sites that need more power.",
        "price": Decimal("9.50"),
        "billing_period": "monthly",
        "specs": {
            "storage": "250 GB SSD",
            "bandwidth": "Unmetered",
            "websites": "Unlimited",
            "email_accounts": "Unlimited",
            "databases": "Unlimited",
        },
        "features": [
            "Everything in Standard",
            "Free dedicated IP",
            "Free domain for 2 years",
            "Free premium SSL",
            "Priority phone support",
        ],
        "sort_order": 3,
    },

    # ---------------------------------------------------------
    # WORDPRESS HOSTING
    # ---------------------------------------------------------
    {
        "category": "wordpress",
        "name": "WP Starter",
        "slug": "wp-starter",
        "tagline": "Managed WordPress for one site.",
        "price": Decimal("4.00"),
        "billing_period": "monthly",
        "specs": {
            "storage": "50 GB SSD",
            "bandwidth": "Unmetered",
            "websites": "1",
            "visits_per_month": "25,000",
        },
        "features": [
            "Managed WordPress core updates",
            "Automatic daily backups",
            "Free CDN",
            "Free SSL",
        ],
        "sort_order": 1,
    },
    {
        "category": "wordpress",
        "name": "WP Pro",
        "slug": "wp-pro",
        "tagline": "Managed WordPress for up to 5 sites.",
        "price": Decimal("12.00"),
        "billing_period": "monthly",
        "specs": {
            "storage": "200 GB SSD",
            "bandwidth": "Unmetered",
            "websites": "5",
            "visits_per_month": "200,000",
        },
        "features": [
            "Everything in WP Starter",
            "Staging environments",
            "Free migrations",
            "Priority WordPress support",
        ],
        "is_featured": True,
        "sort_order": 2,
    },

    # ---------------------------------------------------------
    # VPS
    # ---------------------------------------------------------
    {
        "category": "vps",
        "name": "VPS-1",
        "slug": "vps-1",
        "tagline": "Entry-level cloud VPS.",
        "price": Decimal("6.00"),
        "billing_period": "monthly",
        "setup_fee": Decimal("27.00"),
        "trial_days": 30,
        "specs": {
            "cpu": "1 vCPU",
            "ram": "2 GB",
            "storage": "30 GB NVMe",
            "bandwidth": "2 TB",
            "ipv4": "1",
        },
        "features": [
            "Full root access",
            "SSD storage",
            "Choice of OS",
            "Instant provisioning",
        ],
        "sort_order": 1,
    },
    {
        "category": "vps",
        "name": "VPS-2",
        "slug": "vps-2",
        "tagline": "Great for growing apps and sites.",
        "price": Decimal("12.00"),
        "billing_period": "monthly",
        "setup_fee": Decimal("27.00"),
        "trial_days": 30,
        "specs": {
            "cpu": "2 vCPU",
            "ram": "4 GB",
            "storage": "60 GB NVMe",
            "bandwidth": "4 TB",
            "ipv4": "1",
        },
        "features": [
            "Full root access",
            "SSD storage",
            "Free daily backups",
            "DDoS protection",
        ],
        "is_featured": True,
        "sort_order": 2,
    },
    {
        "category": "vps",
        "name": "VPS-4",
        "slug": "vps-4",
        "tagline": "Production-grade VPS for busy sites.",
        "price": Decimal("24.00"),
        "billing_period": "monthly",
        "setup_fee": Decimal("27.00"),
        "trial_days": 30,
        "specs": {
            "cpu": "4 vCPU",
            "ram": "8 GB",
            "storage": "120 GB NVMe",
            "bandwidth": "8 TB",
            "ipv4": "1",
        },
        "features": [
            "Full root access",
            "SSD storage",
            "Free daily backups",
            "DDoS protection",
            "Free snapshots",
        ],
        "sort_order": 3,
    },
    {
        "category": "vps",
        "name": "VPS-8",
        "slug": "vps-8",
        "tagline": "High-performance VPS for demanding workloads.",
        "price": Decimal("48.00"),
        "billing_period": "monthly",
        "setup_fee": Decimal("27.00"),
        "trial_days": 30,
        "specs": {
            "cpu": "8 vCPU",
            "ram": "16 GB",
            "storage": "240 GB NVMe",
            "bandwidth": "16 TB",
            "ipv4": "2",
        },
        "features": [
            "Full root access",
            "SSD storage",
            "Free daily backups",
            "DDoS protection",
            "Free snapshots",
            "Priority support",
        ],
        "sort_order": 4,
    },

    # ---------------------------------------------------------
    # DEDICATED
    # ---------------------------------------------------------
    {
        "category": "dedicated",
        "name": "Dedicated-1",
        "slug": "dedicated-1",
        "tagline": "Bare-metal power, single-tenant.",
        "price": Decimal("99.00"),
        "billing_period": "monthly",
        "setup_fee": Decimal("75.00"),
        "trial_days": 30,
        "specs": {
            "cpu": "Intel Xeon E-2236 (6c/12t)",
            "ram": "32 GB ECC",
            "storage": "2 x 512 GB NVMe",
            "bandwidth": "30 TB",
            "ipv4": "/29 (5 usable)",
        },
        "features": [
            "Full root access",
            "IPMI / KVM access",
            "Hardware RAID",
            "Free setup",
            "24/7 hardware support",
        ],
        "sort_order": 1,
    },
    {
        "category": "dedicated",
        "name": "Dedicated-2",
        "slug": "dedicated-2",
        "tagline": "Dual-socket workstation-class power.",
        "price": Decimal("199.00"),
        "billing_period": "monthly",
        "setup_fee": Decimal("75.00"),
        "trial_days": 30,
        "specs": {
            "cpu": "Dual Intel Xeon Silver 4214 (24c/48t)",
            "ram": "128 GB ECC",
            "storage": "4 x 1 TB NVMe",
            "bandwidth": "100 TB",
            "ipv4": "/29 (5 usable)",
        },
        "features": [
            "Everything in Dedicated-1",
            "Redundant power supplies",
            "Enterprise SLA",
            "Priority 24/7 support",
        ],
        "is_featured": True,
        "sort_order": 2,
    },

    # ---------------------------------------------------------
    # DOMAINS  (the "plan" price is the registration price)
    # ---------------------------------------------------------
    {
        "category": "domain",
        "name": ".com",
        "slug": "domain-com",
        "tagline": "The classic, trusted everywhere.",
        "price": Decimal("10.99"),
        "billing_period": "yearly",
        "specs": {"tld": ".com", "min_years": "1", "max_years": "10"},
        "features": ["Free WHOIS privacy", "Free DNS management", "Auto-renew optional"],
        "is_featured": True,
        "sort_order": 1,
    },
    {
        "category": "domain",
        "name": ".net",
        "slug": "domain-net",
        "tagline": "For networks and tech brands.",
        "price": Decimal("12.99"),
        "billing_period": "yearly",
        "specs": {"tld": ".net", "min_years": "1", "max_years": "10"},
        "features": ["Free WHOIS privacy", "Free DNS management", "Auto-renew optional"],
        "sort_order": 2,
    },
    {
        "category": "domain",
        "name": ".org",
        "slug": "domain-org",
        "tagline": "For organizations and non-profits.",
        "price": Decimal("11.99"),
        "billing_period": "yearly",
        "specs": {"tld": ".org", "min_years": "1", "max_years": "10"},
        "features": ["Free WHOIS privacy", "Free DNS management", "Auto-renew optional"],
        "sort_order": 3,
    },
    {
        "category": "domain",
        "name": ".co.ke",
        "slug": "domain-co-ke",
        "tagline": "The Kenyan identity. Locally trusted.",
        "price": Decimal("9.99"),
        "billing_period": "yearly",
        "specs": {"tld": ".co.ke", "min_years": "1", "max_years": "5"},
        "features": ["Free WHOIS privacy", "Free DNS management", "Auto-renew optional"],
        "is_featured": True,
        "sort_order": 4,
    },
]


class Command(BaseCommand):
    help = "Seed the Plan catalog with realistic hosting / VPS / domain plans."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all existing plans before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = Plan.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing plan(s)."))

        created = 0
        updated = 0

        for data in PLANS:
            obj, was_created = Plan.objects.update_or_create(
                slug=data["slug"],
                defaults=data,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created: {created}, Updated: {updated}, Total: {Plan.objects.count()}"
            )
        )