import re
from decimal import Decimal


def extract_specs(description):
    text = description.lower()

    ram_match = re.search(r"(\d+)\s*gb\s*ram", text)
    storage_match = re.search(
        r"(\d+)\s*(tb|gb)\s*(ssd|storage)", text
    )

    ram = int(ram_match.group(1)) if ram_match else None

    storage = None
    if storage_match:
        storage = int(storage_match.group(1))
        if storage_match.group(2) == "tb":
            storage *= 1024

    return {
        "ram_gb": ram,
        "storage_gb": storage
    }


def analyze_procurement(procurement):
    quotes = procurement.quotes

    if not quotes:
        raise ValueError("At least one supplier quote is required.")

    budget = Decimal(str(procurement.budget_amount))
    prices = [Decimal(str(q.total_price)) for q in quotes]
    lowest_price = min(prices)

    deliveries = [
        q.delivery_days for q in quotes
        if q.delivery_days is not None
    ]

    fastest_delivery = min(deliveries) if deliveries else None

    specs = [
        extract_specs(q.item_description) for q in quotes
    ]

    known_ram = [
        s["ram_gb"] for s in specs if s["ram_gb"]
    ]
    known_storage = [
        s["storage_gb"] for s in specs if s["storage_gb"]
    ]

    max_ram = max(known_ram, default=None)
    max_storage = max(known_storage, default=None)

    results = []

    for quote, specification in zip(quotes, specs):
        price = Decimal(str(quote.total_price))

        price_score = float(lowest_price / price) * 45

        delivery_score = 0.0
        if fastest_delivery is not None and quote.delivery_days is not None:
            delivery_score = (
                fastest_delivery / max(quote.delivery_days, 1)
            ) * 20

        ram = specification["ram_gb"]
        storage = specification["storage_gb"]

        ram_score = ram / max_ram if ram and max_ram else 0
        storage_score = (
            storage / max_storage
            if storage and max_storage else 0
        )

        spec_score = (
            ram_score * 0.5 + storage_score * 0.5
        ) * 35

        total_score = round(
            price_score + delivery_score + spec_score, 2
        )

        risks = []

        if price > budget:
            risks.append("Quote exceeds procurement budget.")

        if ram is None or storage is None:
            risks.append("Specifications are incomplete.")

        if quote.delivery_days is None:
            risks.append("Delivery timeline is missing.")

        if price > budget * Decimal("0.90"):
            risks.append("Quote uses more than 90% of budget.")

        results.append({
            "quote_id": quote.id,
            "supplier_name": quote.supplier_name,
            "total_price": str(price),
            "delivery_days": quote.delivery_days,
            "specifications": specification,
            "budget_remaining": str(budget - price),
            "budget_utilization_percent": round(
                float(price / budget * 100), 2
            ),
            "score": total_score,
            "risks": risks
        })

    results.sort(
        key=lambda item: (-item["score"], item["total_price"])
    )

    for rank, result in enumerate(results, start=1):
        result["rank"] = rank

    winner = results[0]

    return {
        "procurement_id": procurement.id,
        "methodology": {
            "price_weight": 45,
            "delivery_weight": 20,
            "specification_weight": 35,
            "note": (
                "Relative scores based on submitted quotations. "
                "Specifications are inferred, not independently verified."
            )
        },
        "budget": {
            "amount": str(budget),
            "currency": procurement.currency
        },
        "recommendation": {
            "quote_id": winner["quote_id"],
            "supplier_name": winner["supplier_name"],
            "reason": "Highest weighted score among submitted quotations."
        },
        "ranked_quotes": results
    }
