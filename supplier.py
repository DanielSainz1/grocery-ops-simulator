import random
from typing import List, Dict, Optional


class Supplier:
    """
    Represents a supplier that provides products to a grocery store.

    Products belong to one of 5 categories and each product has a unit COST
    (COGS) from the supplier perspective. The consumer price (sale price)
    is set by the store (Grocery).
    """

    def __init__(self, env, supplier_id: int) -> None:
        """
        Args:
            env: The simulation environment (unused here but kept for extensibility).
            supplier_id (int): The unique ID of the supplier.
        """
        self.env = env
        self.id = supplier_id
        self.products: List[str] = []               # Inventory (list of product names/categories)
        self.prices: Dict[str, float] = {}          # Supplier COST per product (COGS)

    def add_products(self, quantity: Optional[int] = None) -> None:
        """
        Adds 'quantity' units of products to the supplier's inventory.
        If not provided, a random quantity between 1 and 10 is added.
        Each unit is randomly assigned to one of 5 categories, with a supplier cost.
        """
        product_types = ["proteins", "carbohydrates", "fruits", "vegetables", "sweets"]
        if quantity is None:
            quantity = random.randint(1, 10)

        for _ in range(quantity):
            p = random.choice(product_types)
            self.products.append(p)
            # Supplier unit COST (COGS) ~ U[1, 5]
            # (The sale price will be set by the store with a markup.)
            self.prices[p] = self._maybe_update_cost(p, random.uniform(1.0, 5.0))

    def _maybe_update_cost(self, product: str, new_cost: float) -> float:
        """Keep the latest cost estimate for a product (or set if new)."""
        if product not in self.prices:
            self.prices[product] = new_cost
        else:
            # Optional smoothing could be added; we simply take the latest.
            self.prices[product] = new_cost
        return self.prices[product]

    def supply_products(self, quantity: int) -> List[str]:
        """
        Supplies up to 'quantity' products from inventory.
        Returns an empty list if there aren't enough products.
        """
        try:
            if len(self.products) < quantity:
                raise ValueError(f"Not enough products to supply. Only {len(self.products)} available.")
            return [self.products.pop() for _ in range(quantity)]
        except ValueError as e:
            print(f"Error: {e}")
            return []

    def get_price(self, product: str) -> float:
        """
        Returns supplier unit COST (COGS) for 'product'.
        If unknown, returns 0.
        """
        return self.prices.get(product, 0.0)
