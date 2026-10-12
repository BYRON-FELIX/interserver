"""Session-backed shopping cart."""

from decimal import Decimal
import re

from .currencies import usd_to_kes
from .models import Plan


CART_SESSION_KEY = "cart"
DOMAIN_REGISTRATION_PRICE_KES = Decimal("1500.00")
DOMAIN_PATTERN = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z"
)


def normalize_domain_name(domain):
    normalized = (domain or "").strip().rstrip(".").lower()
    if normalized and "." not in normalized:
        normalized = f"{normalized}.com"
    if not DOMAIN_PATTERN.fullmatch(normalized):
        return None
    return normalized


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.setdefault(CART_SESSION_KEY, {})

    def add(self, plan, quantity=1, period=None, domain=None):
        key = f"domain:{plan.id}:{domain}" if domain else str(plan.id)
        if key not in self.cart:
            self.cart[key] = {
                "quantity": 0 if not domain else quantity,
                "period": period or plan.billing_period,
                **({"domain": domain} if domain else {}),
            }
        if not domain:
            self.cart[key]["quantity"] += quantity
        self.save()

    def remove(self, plan_id):
        key = str(plan_id)
        if key in self.cart:
            del self.cart[key]
            self.save()

    def set_quantity(self, plan_id, quantity):
        key = str(plan_id)
        if key not in self.cart:
            return
        if quantity <= 0:
            self.remove(plan_id)
        else:
            self.cart[key]["quantity"] = quantity
            self.save()

    def clear(self):
        self.cart = {}
        self.save()

    def save(self):
        self.session[CART_SESSION_KEY] = self.cart
        self.session.modified = True

    def __len__(self):
        return sum(item["quantity"] for item in self.cart.values())

    def count(self):
        return len(self)

    def items(self):
        cart_entries = []
        for key, data in self.cart.items():
            if key.startswith("domain:"):
                _, plan_id, domain = key.split(":", 2)
            else:
                plan_id = key
                domain = data.get("domain", "")
            try:
                plan_id = int(plan_id)
            except ValueError:
                continue
            cart_entries.append((key, plan_id, domain, data))

        plan_ids = {plan_id for _, plan_id, _, _ in cart_entries}
        plans = Plan.objects.filter(id__in=plan_ids, is_active=True)
        plan_map = {plan.id: plan for plan in plans}

        result = []
        for key, plan_id, domain, data in cart_entries:
            plan = plan_map.get(plan_id)
            if plan is None:
                continue
            is_domain = plan.category == Plan.Category.DOMAIN
            unit_price_kes = (
                DOMAIN_REGISTRATION_PRICE_KES
                if is_domain
                else usd_to_kes(plan.price)
            )
            result.append({
                "plan": plan,
                "quantity": data["quantity"],
                "period": data.get("period") or plan.billing_period,
                "domain": domain,
                "display_name": domain or plan.name,
                "cart_key": key,
                "line_total": plan.price * data["quantity"],
                "unit_price_kes": unit_price_kes,
                "line_total_kes": unit_price_kes * data["quantity"],
            })
        return result

    def total(self):
        return sum(
            (item["line_total"] for item in self.items()),
            Decimal("0.00"),
        )

    def total_kes(self):
        items = self.items()
        domain_total = sum(
            (
                item["line_total_kes"]
                for item in items
                if item["plan"].category == Plan.Category.DOMAIN
            ),
            Decimal("0.00"),
        )
        non_domain_total_usd = sum(
            (
                item["line_total"]
                for item in items
                if item["plan"].category != Plan.Category.DOMAIN
            ),
            Decimal("0.00"),
        )
        non_domain_total_kes = (
            usd_to_kes(non_domain_total_usd)
            if non_domain_total_usd
            else Decimal("0.00")
        )
        return domain_total + non_domain_total_kes
