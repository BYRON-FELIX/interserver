"""
Generate believable—but fictional—provisioning data for orders.
Nothing here touches a real server. The generated IPs use documentation
ranges reserved for examples, not addresses assigned to real hosts.
"""

import random
import secrets
import string

from django.utils import timezone

from .models import Service

REGIONS = [
    ("nbo-1", "Nairobi, Kenya"),
    ("lon-1", "London, UK"),
    ("fra-1", "Frankfurt, Germany"),
    ("nyc-1", "New York, USA"),
    ("sin-1", "Singapore"),
]

OS_OPTIONS = [
    "Ubuntu 22.04 LTS",
    "Ubuntu 24.04 LTS",
    "Debian 12",
    "AlmaLinux 9",
    "Rocky Linux 9",
    "CentOS Stream 9",
]

DOMAIN_NAMESERVERS = [
    "ns1.interserver.net",
    "ns2.interserver.net",
    "ns3.interserver.net",
    "ns4.interserver.net",
]


def generate_ipv4(seed: int | str | None = None) -> str:
    """Return an example address from the reserved 192.0.2.0/24 range."""
    rng = random.Random(seed)
    return f"192.0.2.{rng.randint(1, 254)}"


def generate_ipv6(seed: int | str | None = None) -> str:
    """Return an example address from the reserved 2001:db8::/32 range."""
    rng = random.Random(seed)
    groups = [f"{rng.randint(0, 0xffff):x}" for _ in range(4)]
    return "2001:db8:" + ":".join(groups) + "::"


def generate_hostname(service_name: str, seed: int | str | None = None) -> str:
    rng = random.Random(seed)
    slug = "".join(
        character
        for character in service_name.lower()
        if character.isalnum() or character == "-"
    )[:24]
    slug = slug or "server"
    token = "".join(rng.choices("0123456789abcdef", k=4))
    return f"{slug}-{token}.vps.interserver.net"


def generate_root_password(length: int = 18) -> str:
    """Generate a password containing upper/lowercase letters, digits, and symbols."""
    if not 4 <= length <= 64:
        raise ValueError("Password length must be between 4 and 64 characters.")

    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()-_=+"

    password_chars = [
        secrets.choice(lower),
        secrets.choice(upper),
        secrets.choice(digits),
        secrets.choice(symbols),
    ]
    pool = lower + upper + digits + symbols
    password_chars.extend(
        secrets.choice(pool) for _ in range(length - len(password_chars))
    )
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


def provision_vps(
    service: Service, seed: int | str | None = None
) -> Service:
    """Fill a Service row with fictional VPS provisioning data; caller saves it."""
    seed = seed if seed is not None else service.pk
    rng = random.Random(seed)
    service.ip_address = generate_ipv4(seed)
    service.ipv6_address = generate_ipv6(seed)
    service.hostname = generate_hostname(service.name, seed)
    service.root_username = "root"
    service.set_root_password(generate_root_password())
    service.operating_system = rng.choice(OS_OPTIONS)
    service.region = rng.choice(REGIONS)[0]
    service.provisioned_at = timezone.now()
    return service


def provision_domain(service: Service) -> Service:
    """Fill a domain Service row with default nameservers and provisioning time."""
    service.nameservers = list(DOMAIN_NAMESERVERS[:2])
    service.provisioned_at = timezone.now()
    return service


def default_domain_records(
    service: Service, ip_address: str | None = None
) -> list[dict[str, str | int]]:
    """Describe starter DNS records for a new domain; caller creates the rows."""
    ip_address = ip_address or service.ip_address or "192.0.2.10"
    return [
        {"type": "A", "name": "@", "value": ip_address, "ttl": 3600},
        {"type": "A", "name": "www", "value": ip_address, "ttl": 3600},
        {
            "type": "MX",
            "name": "@",
            "value": "mail.interserver.net",
            "ttl": 3600,
            "priority": 10,
        },
        {
            "type": "TXT",
            "name": "@",
            "value": "v=spf1 include:_spf.interserver.net ~all",
            "ttl": 3600,
        },
    ]


def region_label(code: str) -> str:
    for region_code, label in REGIONS:
        if region_code == code:
            return label
    return code
