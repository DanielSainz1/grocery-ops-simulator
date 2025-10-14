# Grocery Operations Simulator — Python (SimPy · scikit-fuzzy · PSO)

A compact **operations & pricing** simulator for a grocery store. It blends **discrete-event simulation (SimPy)**, **fuzzy-logic discounting**, and a lightweight **PSO** step to suggest initial stock levels. The program outputs **daily KPIs** to CSV: `revenue`, `cogs`, `delivery_cost`, `profit`, `products_sold`.

> - Demonstrates **end-to-end thinking**.
> - Applies **AI techniques** (fuzzy systems, metaheuristics) to a concrete **business problem** (pricing & inventory).
> - Shows **reproducible, modular Python** with results you can analyze immediately.

---

## Features

- **Discrete-event simulation** of daily operations (cashiers, service time, customer arrivals).
- **Fuzzy-logic pricing**: discount (0–30%) adapts to **stock** and **recent sales**, with guardrails.
- **Demand mix by product** (proteins, carbohydrates, fruits, vegetables, sweets).
- **Real economics**.
- **PSO** (optional): suggests initial stock per supplier before the 30-day run.
- **Reproducible** results via fixed seeds; export to `daily_balance.csv`.

---

## Tech Stack

- **Python**, **SimPy** (events & resources)  
- **scikit-fuzzy** (fuzzy control system)  
- **pyswarm** (Particle Swarm Optimization)  
- **pandas**, **NumPy**

---
