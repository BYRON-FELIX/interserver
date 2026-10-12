"""Session-backed shopping cart."""

from decimal import Decimal

from .currencies import usd_to_kes
from .models import Plan


CART_SESSION_KEY = "cart"
DOMAIN_REGISTRATION_PRICE_KES = Decimal("1500.00")


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.setdefault(CART_SESSION_KEY, {})

    def add(self, plan, quantity=1, period=None):
        key = str(plan.id)
        if key not in self.cart:
            self.cart[key] = {
                "quantity": 0,
                "period": period or plan.billing_period,
            }
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
        plan_ids = [int(key) for key in self.cart]
        plans = Plan.objects.filter(id__in=plan_ids, is_active=True)
        plan_map = {plan.id: plan for plan in plans}

        result = []
        for key, data in self.cart.items():
            plan = plan_map.get(int(key))
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
