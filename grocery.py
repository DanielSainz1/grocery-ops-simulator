import random
import simpy
from collections import defaultdict
from typing import Dict, Optional
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class Grocery:
    """
    Grocery store abstraction. Holds stock levels (by product/category),
    sale prices, supplier unit costs (COGS), a cashier resource, and a fuzzy
    pricing (discount) system.
    """

    def __init__(self, env: simpy.Environment, num_cashiers: int = 5) -> None:
        self.env = env

        # Stock and economics
        self.stock: Dict[str, int] = defaultdict(int)       # units in stock by product
        self.prices: Dict[str, float] = {}                  # sale price by product (store -> consumer)
        self.costs: Dict[str, float] = {}                   # supplier unit COST (COGS) by product
        self.sales_count: Dict[str, int] = defaultdict(int) # sales by product (for analytics)

        # Cashiers (capacity)
        self.cashiers = simpy.Resource(env, num_cashiers)

        # ---- Fuzzy logic for discount (0–30%) based on stock 0–100 and sales 0–100 ----
        self.stock_fuzzy = ctrl.Antecedent(np.arange(0, 101, 1), 'stock')
        self.sales_fuzzy = ctrl.Antecedent(np.arange(0, 101, 1), 'sales')
        self.discount_fuzzy = ctrl.Consequent(np.arange(0, 31, 1), 'discount')

        # Memberships (automatic for stock/sales: 'poor', 'average', 'good')
        self.stock_fuzzy.automf(3)
        self.sales_fuzzy.automf(3)

        # Discount membership functions: low (0–5), medium (5–15), high (15–30)
        self.discount_fuzzy['low']    = fuzz.trimf(self.discount_fuzzy.universe, [0,  0,  5])
        self.discount_fuzzy['medium'] = fuzz.trimf(self.discount_fuzzy.universe, [5, 10, 15])
        self.discount_fuzzy['high']   = fuzz.trimf(self.discount_fuzzy.universe, [15, 22, 30])

        # Fuzzy rules (cover key quadrants)
        rule1 = ctrl.Rule(self.stock_fuzzy['poor'] | self.sales_fuzzy['poor'], self.discount_fuzzy['high'])
        rule2 = ctrl.Rule(self.stock_fuzzy['average'] | self.sales_fuzzy['average'], self.discount_fuzzy['medium'])
        rule3 = ctrl.Rule(self.stock_fuzzy['good'] & self.sales_fuzzy['good'], self.discount_fuzzy['low'])
        rule4 = ctrl.Rule(self.stock_fuzzy['good'] & self.sales_fuzzy['poor'], self.discount_fuzzy['medium'])
        rule5 = ctrl.Rule(self.stock_fuzzy['poor'] & self.sales_fuzzy['good'], self.discount_fuzzy['medium'])

        self.discount_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5])
        self.discount_sim = ctrl.ControlSystemSimulation(self.discount_ctrl)

        # Demand preferences (probability weights by product)
        self.demand_weights: Dict[str, float] = {
            "proteins": 0.30,
            "carbohydrates": 0.25,
            "fruits": 0.20,
            "vegetables": 0.15,
            "sweets": 0.10,
        }

    # ---------- Economic operations ----------

    def set_sale_price(self, product: str, price: float) -> None:
        self.prices[product] = max(0.01, float(price))

    def calculate_delivery_cost(self, distance_km: float) -> float:
        """Per-order delivery cost bands (customer delivery)."""
        if distance_km < 10:
            return 5.0
        elif distance_km < 20:
            return 10.0
        elif distance_km < 30:
            return 15.0
        else:
            return 20.0

    def add_stock(self, supplier, quantity: int) -> None:
        """
        Inbound replenishment (store buys from supplier).
        - Increases stock by product
        - Stores supplier unit COST (COGS) if unknown
        - Sets initial sale price if unknown (markup 20%–50%)
        """
        products = supplier.supply_products(quantity)
        for product in products:
            self.stock[product] += 1
            if product not in self.costs:
                self.costs[product] = supplier.get_price(product)
            if product not in self.prices:
                self.prices[product] = self.costs[product] * random.uniform(1.2, 1.5)

    # ---------- Sales & discounts ----------

    def _compute_discount(self, stock_units: int, sales_units: int) -> float:
        """
        Compute discount (%) with fuzzy system. Inputs are capped to 0–100.
        """
        s = max(0, min(100, int(stock_units)))
        v = max(0, min(100, int(sales_units)))
        self.discount_sim.input['stock'] = s
        self.discount_sim.input['sales'] = v
        self.discount_sim.compute()
        return float(self.discount_sim.output['discount'])

    def apply_discounts(self) -> None:
        """
        Apply fuzzy discount to each product's sale price (multiplicative).
        This is applied once per day before sales happen.
        """
        for product, stock_units in self.stock.items():
            if stock_units <= 0 or product not in self.prices:
                continue
            sales_units = self.sales_count.get(product, 0)
            discount_pct = self._compute_discount(stock_units, sales_units)
            new_price = self.prices[product] * (1.0 - discount_pct / 100.0)
            # Keep a floor to avoid nonsensical zero or negative prices
            self.prices[product] = max(new_price, self.costs.get(product, 0.0) * 1.05)

    def sell_one_product(self) -> Optional[str]:
        """
        Sell exactly one product, chosen according to demand weights and availability.
        Returns the product name if sold; else None.
        """
        # Available products with positive stock
        available = [p for p, q in self.stock.items() if q > 0]
        if not available:
            return None

        # Build weights only for available products
        weights = np.array([self.demand_weights.get(p, 0.01) for p in available], dtype=float)
        if weights.sum() == 0:
            weights = np.ones(len(available), dtype=float)
        weights = weights / weights.sum()

        # Choose product
        product = np.random.choice(available, p=weights)

        # Process sale (one unit)
        self.stock[product] -= 1
        self.sales_count[product] += 1
        return product

    def reset_sales_counters(self) -> None:
        self.sales_count.clear()
