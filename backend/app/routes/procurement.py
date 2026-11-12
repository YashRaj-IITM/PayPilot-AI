from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify

from app import db
from app.models.procurement import ProcurementRequest, SupplierQuote, AIAnalysis

procurement_bp = Blueprint("procurement", __name__)


def parse_money(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Amount must be positive.")
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a valid positive monetary amount.")


def build_quote(data):
    if not isinstance(data, dict):
        raise ValueError("Each quote must be an object.")

    supplier = str(data.get("supplier_name", "")).strip()
    description = str(data.get("item_description", "")).strip()

    if not supplier or not description:
        raise ValueError("Supplier name and item description are required.")

    if len(supplier) > 150:
        raise ValueError("Supplier name is too long.")

    if len(description) > 5000:
        raise ValueError("Item description is too long.")

    unit_price = parse_money(data.get("unit_price"))

    quantity = data.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise ValueError("Quantity must be a positive integer.")

    if quantity < 1 or quantity > 100000:
        raise ValueError("Quantity is outside the allowed range.")

    delivery_days = data.get("delivery_days")
    if delivery_days is not None:
        if (
            isinstance(delivery_days, bool)
            or not isinstance(delivery_days, int)
            or not 0 <= delivery_days <= 3650
        ):
            raise ValueError("Delivery days must be between 0 and 3650.")

    return SupplierQuote(
        supplier_name=supplier,
        item_description=description,
        unit_price=unit_price,
        quantity=quantity,
        total_price=unit_price * quantity,
        delivery_days=delivery_days,
        source_url=data.get("source_url")
    )


@procurement_bp.route("/procurements", methods=["POST"])
def create_procurement():
    data = request.get_json(silent=True) or {}

    try:
        title = str(data.get("title", "")).strip()
        description = str(data.get("description", "")).strip()
        currency = str(data.get("currency", "USD")).upper()

        if not title or not description:
            raise ValueError("Title and description are required.")

        if len(title) > 150 or len(description) > 5000:
            raise ValueError("Title or description is too long.")

        # USD is our initial PayPal checkout currency.
        if currency != "USD":
            raise ValueError("The MVP currently supports USD only.")

        budget = parse_money(data.get("budget_amount"))

        quotes_data = data.get("quotes", [])
        if not isinstance(quotes_data, list) or len(quotes_data) > 50:
            raise ValueError("Quotes must be a list of at most 50 items.")

        procurement = ProcurementRequest(
            title=title,
            description=description,
            budget_amount=budget,
            currency=currency,
            status="DRAFT"
        )

        db.session.add(procurement)
        db.session.flush()

        for quote_data in quotes_data:
            quote = build_quote(quote_data)
            quote.procurement_id = procurement.id
            db.session.add(quote)

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Procurement request created.",
            "procurement": procurement.to_dict()
        }), 201

    except ValueError as error:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Unable to create procurement request."
        }), 500


@procurement_bp.route("/procurements", methods=["GET"])
def list_procurements():
    records = ProcurementRequest.query.order_by(
        ProcurementRequest.created_at.desc()
    ).all()

    return jsonify({
        "success": True,
        "count": len(records),
        "procurements": [item.to_dict() for item in records]
    }), 200


@procurement_bp.route("/procurements/<int:procurement_id>", methods=["GET"])
def get_procurement(procurement_id):
    procurement = db.session.get(ProcurementRequest, procurement_id)

    if procurement is None:
        return jsonify({
            "success": False,
            "error": "Procurement request not found."
        }), 404

    return jsonify({
        "success": True,
        "procurement": procurement.to_dict()
    }), 200


@procurement_bp.route(
    "/procurements/<int:procurement_id>/quotes",
    methods=["POST"]
)
def add_supplier_quote(procurement_id):
    procurement = db.session.get(ProcurementRequest, procurement_id)

    if procurement is None:
        return jsonify({
            "success": False,
            "error": "Procurement request not found."
        }), 404

    try:
        quote = build_quote(request.get_json(silent=True) or {})
        quote.procurement_id = procurement.id

        db.session.add(quote)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Supplier quote added.",
            "quote": quote.to_dict()
        }), 201

    except ValueError as error:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Unable to save supplier quote."
        }), 500



@procurement_bp.route(
    "/procurements/<int:procurement_id>/analyze",
    methods=["POST"]
)
def analyze_procurement_request(procurement_id):
    procurement = db.session.get(ProcurementRequest, procurement_id)

    if procurement is None:
        return jsonify({
            "success": False,
            "error": "Procurement request not found."
        }), 404

    try:
        from app.services.procurement_intelligence import analyze_procurement
        from app.services.gemini_agent import generate_procurement_insights

        # First calculate objective supplier rankings.
        analysis = analyze_procurement(procurement)

        # Then use Gemini to explain the actual results.
        insights = generate_procurement_insights(
            procurement,
            analysis
        )

    except ValueError as error:
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception:
        import logging
        logging.exception("Gemini procurement analysis failed")
        return jsonify({
            "success": False,
            "error": "AI analysis failed. Check server logs."
        }), 502

    try:
        record = AIAnalysis(
            procurement_id=procurement.id,
            provider=insights["provider"],
            model=insights["model"],
            summary=insights["report"],
            analysis_json={
                "deterministic_analysis": analysis,
                "ai_report": insights["report"]
            }
        )

        db.session.add(record)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "AI procurement analysis completed.",
            "analysis_id": record.id,
            "deterministic_analysis": analysis,
            "ai_insights": {
                "provider": insights["provider"],
                "model": insights["model"],
                "report": insights["report"],
                "finish_reason": insights.get("finish_reason"),
                "token_usage": insights.get("token_usage")
            }
        }), 200

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Unable to save AI analysis."
        }), 500
