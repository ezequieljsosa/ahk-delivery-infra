#!/usr/bin/env python3
"""Simula clientes: crea pedidos y los entrega con un tiempo real "sintético".

Sirve para llenar la tabla orders_history del worker con datos nuevos (solo stdlib).

Uso:  python3 simulate.py [cantidad]      (por defecto 20)
"""

import json
import random
import sys
import urllib.request

CATALOG = "http://localhost:8081"
ORDERS = "http://localhost:8082"


def call(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.load(res)


def real_minutes(order):
    """Lo que 'de verdad' tardó el pedido. Misma lógica que el generador del predictor, con ruido."""
    peak = 8 if order["hourOfDay"] in (12, 13, 20, 21) else 0
    eta = (
        order["prepMinutes"] + 4 * order["distanceKm"] * (1 + 0.4 * order["raining"]) + 1.2 * order["itemsCount"] + peak
    )
    return max(5, round(eta + random.gauss(0, 3)))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    restaurants = call("GET", f"{CATALOG}/restaurants")
    for _ in range(n):
        r = random.choice(restaurants)
        items = [
            {"sku": random.choice(r["menu"])["sku"], "qty": random.randint(1, 3)} for _ in range(random.randint(1, 3))
        ]
        order = call(
            "POST",
            f"{ORDERS}/orders",
            {
                "restaurantId": r["id"],
                "lat": -34.60 + random.uniform(-0.06, 0.06),
                "lon": -58.38 + random.uniform(-0.06, 0.06),
                "raining": random.random() < 0.3,
                "items": items,
            },
        )
        order["raining"] = int(order["raining"])
        actual = real_minutes(order)
        call("POST", f"{ORDERS}/orders/{order['id']}/deliver", {"actualMinutes": actual})
        print(f"pedido {order['id']}: dist={order['distanceKm']:.1f}km predicho={order['etaMinutes']} real={actual}")


if __name__ == "__main__":
    main()
