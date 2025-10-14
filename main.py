import random
import simpy
import pandas as pd
from typing import List, Dict, Union, Tuple
from pyswarm import pso
from datetime import datetime

from supplier import Supplier
from grocery import Grocery


class Simulation:
    """
    Manages the simulation of a grocery store with multiple suppliers.
    - Replenishment from suppliers
    - Fuzzy discounting applied daily
    - Customer purchases with demand weights
    - Revenue, COGS and delivery costs accounted for
    """

    def __init__(self, env: simpy.Environment, suppliers: List[Supplier], grocery: Grocery, days: int = 30) -> None:
        self.env = env
        self.suppliers = suppliers
        self.grocery = grocery
        self.days = int(days)
        self.daily_balances: List[Dict[str, Union[int, float, str]]] = []

    def _restock_all_suppliers(self, units_per_supplier: int = 5) -> None:
        """
        Each supplier gets new inventory, then the store purchases a batch (adds to store stock).
        """
        for supplier in self.suppliers:
            supplier.add_products(units_per_supplier)  # Supplier produces inventory
            try:
                self.grocery.add_stock(supplier, max(0, units_per_supplier // 2))
            except ValueError as e:
                print(f"Error restocking supplier {supplier.id}: {e}")

    def _simulate_customers_for_day(self, rng: random.Random) -> Tuple[float, float, float, int]:
        """
        Simulate customer purchases for a single day.
        Returns: (revenue, cogs, delivery_cost, products_sold)
        """
        revenue = 0.0
        cogs = 0.0
        delivery_cost = 0.0
        products_sold = 0

        # Number of customers today
        num_customers = rng.randint(8, 20)

        for _ in range(num_customers):
            # Each customer queues to a cashier (simple service time)
            with self.grocery.cashiers.request() as req:
                yield req
                yield self.env.timeout(rng.uniform(0.5, 2.0))

                sold_product = self.grocery.sell_one_product()
                if sold_product:
                    price = self.grocery.prices.get(sold_product, 0.0)
                    unit_cost = self.grocery.costs.get(sold_product, 0.0)

                    # Revenue and COGS
                    revenue += price
                    cogs += unit_cost
                    products_sold += 1

                    # Delivery to customer
                    distance = rng.uniform(1.0, 35.0)  # km
                    delivery_cost += self.grocery.calculate_delivery_cost(distance)

        return revenue, cogs, delivery_cost, products_sold

    def run_day(self, day: int, rng: random.Random):
        """
        One day in the simulation:
        - Replenish from suppliers
        - Apply fuzzy discount based on current stock & sales
        - Simulate customers
        - Record daily metrics
        """
        # Inbound replenishment (new supplier inventory + store buy)
        self._restock_all_suppliers(units_per_supplier=10)

        # Apply daily fuzzy discounts before selling
        self.grocery.apply_discounts()

        # Process customers and purchases
        proc = self.env.process(self._simulate_customers_for_day(rng))
        yield proc
        revenue, cogs, delivery_cost, products_sold = proc.value

        # Profit = revenue − (COGS + delivery_cost)
        profit = revenue - (cogs + delivery_cost)

        self.daily_balances.append({
            "day": day,
            "revenue": round(revenue, 2),
            "cogs": round(cogs, 2),
            "delivery_cost": round(delivery_cost, 2),
            "profit": round(profit, 2),
            "products_sold": int(products_sold),
        })

        # Next day step
        yield self.env.timeout(1)
        # Reset sales counters (used as fuzzy input)
        self.grocery.reset_sales_counters()

    def run_simulation(self, seed: int = 42) -> None:
        rng = random.Random(seed)
        for day in range(1, self.days + 1):
            self.env.process(self.run_day(day, rng))
        self.env.run()

        # Final totals row
        total_revenue = sum(d["revenue"] for d in self.daily_balances)
        total_cogs = sum(d["cogs"] for d in self.daily_balances)
        total_delivery = sum(d["delivery_cost"] for d in self.daily_balances)
        total_profit = sum(d["profit"] for d in self.daily_balances)
        total_products = sum(d["products_sold"] for d in self.daily_balances)

        self.daily_balances.append({
            "day": "Total",
            "revenue": round(total_revenue, 2),
            "cogs": round(total_cogs, 2),
            "delivery_cost": round(total_delivery, 2),
            "profit": round(total_profit, 2),
            "products_sold": int(total_products),
        })

    def export_to_csv(self, path: str = "daily_balance.csv") -> None:
        if not self.daily_balances:
            print("No data collected during the simulation.")
            return
        try:
            df = pd.DataFrame(self.daily_balances)
            df.to_csv(path, index=False)
            print(f"Daily balance exported to '{path}'")
        except PermissionError:
            # Fallback if the file is open/locked (e.g., opened in Excel)
            alt = f"daily_balance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df = pd.DataFrame(self.daily_balances)
            df.to_csv(alt, index=False)
            print(f"File was locked. Exported instead to '{alt}'")


# --------------------- PSO Fitness (optional) ---------------------

def fitness_function(stock_per_supplier: List[float]) -> float:
    """
    Particle Swarm Optimization fitness:
    - For given initial stocks per supplier, run a short simulation and return the NEGATIVE total profit.
    - PSO MINIMIZES, so we return -profit.
    """
    env = simpy.Environment()
    suppliers = [Supplier(env, i) for i in range(5)]
    grocery = Grocery(env, num_cashiers=3)

    # Initialize suppliers and store with given initial stock
    for i, supplier in enumerate(suppliers):
        qty = max(0, int(stock_per_supplier[i]))
        supplier.add_products(qty)
        grocery.add_stock(supplier, qty)

    sim = Simulation(env, suppliers, grocery, days=10)
    sim.run_simulation(seed=999)

    # Evaluate performance: total profit (last row)
    total_profit = sim.daily_balances[-1]["profit"] if sim.daily_balances else 0.0
    return -float(total_profit)  # minimize


if __name__ == "__main__":
    # 1) PSO to suggest an initial stock strategy (optional and quick)
    print("Starting optimization with PSO...")
    lb = [5] * 5
    ub = [50] * 5
    best_stock, _ = pso(fitness_function, lb, ub, swarmsize=8, maxiter=4)
    print("Optimal initial stock per supplier (PSO):", [float(round(x, 2)) for x in best_stock])

    # 2) Run main simulation with the suggested strategy
    print("\nRunning main simulation with optimal strategy...")
    env = simpy.Environment()
    suppliers = [Supplier(env, i) for i in range(5)]
    grocery = Grocery(env, num_cashiers=5)

    # Load initial stock to store according to PSO
    for i, stock in enumerate(best_stock):
        qty = max(0, int(stock))
        suppliers[i].add_products(qty)
        grocery.add_stock(suppliers[i], qty)

    # Run
    sim = Simulation(env, suppliers, grocery, days=30)
    sim.run_simulation(seed=42)
    sim.export_to_csv("daily_balance.csv")
