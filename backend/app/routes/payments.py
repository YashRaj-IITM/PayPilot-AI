from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from app import db
from app.models.procurement import (
    ProcurementRequest,
    SupplierQuote,
    PaymentTransaction,
)
from app.services.paypal_service import (
    create_order,
    capture_order,
    PayPalError,
)

payments_bp = Blueprint("payments", __name__)


@payments_bp.route(
    "/procurements/<int:procurement_id>/approve",
    methods=["POST"],
)
def approve_procurement(procurement_id):
    data = request.get_json(silent=True) or {}
    quote_id = data.get("quote_id")

    if isinstance(quote_id, bool) or not isinstance(quote_id, int):
        return jsonify({
            "success": False,
            "error": "A valid integer quote_id is required.",
        }), 400

    procurement = db.session.get(ProcurementRequest, procurement_id)

    if procurement is None:
        return jsonify({"success": False, "error": "Procurement not found."}), 404

    if procurement.status != "ANALYZED":
        return jsonify({
            "success": False,
            "error": "Procurement must be analyzed before approval.",
        }), 409

    quote = db.session.get(SupplierQuote, quote_id)

    if quote is None or quote.procurement_id != procurement_id:
        return jsonify({
            "success": False,
            "error": "The selected quotation does not belong to this procurement.",
        }), 400

    try:
        amount = Decimal(str(quote.total_price))
        budget = Decimal(str(procurement.budget_amount))

        if amount <= 0 or amount > budget:
            return jsonify({
                "success": False,
                "error": "Quotation amount must be positive and within budget.",
            }), 400

        if procurement.currency != "USD":
            return jsonify({
                "success": False,
                "error": "Only USD payments are supported in this MVP.",
            }), 400

        existing = PaymentTransaction.query.filter_by(
            procurement_id=procurement_id
        ).filter(
            PaymentTransaction.status.in_(
                ["APPROVED", "ORDER_CREATED", "COMPLETED"]
            )
        ).first()

        if existing:
            return jsonify({
                "success": False,
                "error": "An approved or active payment already exists.",
            }), 409

        transaction = PaymentTransaction(
            procurement_id=procurement_id,
            quote_id=quote_id,
            amount=amount,
            currency=procurement.currency,
            status="APPROVED",
            approval_confirmed=True,
        )

        procurement.status = "APPROVED"

        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Supplier quotation approved by the user.",
            "transaction_id": transaction.id,
            "supplier": quote.supplier_name,
            "amount": str(amount),
            "currency": procurement.currency,
            "status": transaction.status,
        }), 201

    except (InvalidOperation, ValueError):
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Invalid quotation amount.",
        }), 400

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Unable to approve procurement.",
        }), 500


@payments_bp.route(
    "/procurements/<int:procurement_id>/payment/create",
    methods=["POST"],
)
def create_payment_order(procurement_id):
    data = request.get_json(silent=True) or {}
    transaction_id = data.get("transaction_id")

    if isinstance(transaction_id, bool) or not isinstance(transaction_id, int):
        return jsonify({
            "success": False,
            "error": "A valid transaction_id is required.",
        }), 400

    transaction = db.session.get(PaymentTransaction, transaction_id)

    if transaction is None or transaction.procurement_id != procurement_id:
        return jsonify({
            "success": False,
            "error": "Approved payment transaction not found.",
        }), 404

    if not transaction.approval_confirmed or transaction.status != "APPROVED":
        return jsonify({
            "success": False,
            "error": "Human approval is required before checkout.",
        }), 409

    procurement = db.session.get(ProcurementRequest, procurement_id)
    quote = db.session.get(SupplierQuote, transaction.quote_id)

    if procurement is None or quote is None:
        return jsonify({
            "success": False,
            "error": "Procurement or quotation no longer exists.",
        }), 404

    if quote.procurement_id != procurement_id:
        return jsonify({
            "success": False,
            "error": "Quotation does not match procurement.",
        }), 400

    if Decimal(str(quote.total_price)) != Decimal(str(transaction.amount)):
        return jsonify({
            "success": False,
            "error": "Quotation amount has changed. Approval must be repeated.",
        }), 409

    try:
        result = create_order(
            amount=transaction.amount,
            currency=transaction.currency,
            description=quote.item_description,
            procurement_id=procurement_id,
            transaction_id=transaction.id,
        )

        if result.get("status") != "CREATED" or not result.get("id"):
            raise PayPalError("PayPal did not create a valid checkout order.")

        approval_url = next(
            (
                link["href"]
                for link in result.get("links", [])
                if link.get("rel") == "approve"
            ),
            None,
        )

        if not approval_url:
            raise PayPalError("PayPal did not return an approval link.")

        transaction.paypal_order_id = result["id"]
        transaction.status = "ORDER_CREATED"
        transaction.raw_response = result

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "PayPal Sandbox order created.",
            "transaction_id": transaction.id,
            "paypal_order_id": transaction.paypal_order_id,
            "approval_url": approval_url,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status,
        }), 201

    except PayPalError as error:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(error),
        }), 502

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Unable to create PayPal order.",
        }), 500


@payments_bp.route(
    "/payments/<int:transaction_id>/capture",
    methods=["POST"],
)
def capture_payment(transaction_id):
    transaction = db.session.get(PaymentTransaction, transaction_id)

    if transaction is None:
        return jsonify({
            "success": False,
            "error": "Payment transaction not found.",
        }), 404

    data = request.get_json(silent=True) or {}
    returned_order_id = data.get("order_id")

    if not returned_order_id or returned_order_id != transaction.paypal_order_id:
        return jsonify({
            "success": False,
            "error": "PayPal return order ID does not match the approved transaction.",
        }), 400

    if transaction.status == "COMPLETED":
        return jsonify({
            "success": True,
            "message": "Payment was already completed.",
            "transaction_id": transaction.id,
            "capture_id": transaction.paypal_capture_id,
            "status": transaction.status,
        }), 200

    if (
        not transaction.approval_confirmed
        or transaction.status != "ORDER_CREATED"
        or not transaction.paypal_order_id
    ):
        return jsonify({
            "success": False,
            "error": "An approved PayPal order is required before capture.",
        }), 409

    try:
        result = capture_order(transaction.paypal_order_id)

        if result.get("status") != "COMPLETED":
            raise PayPalError("PayPal has not confirmed completed payment.")

        if result.get("id") != transaction.paypal_order_id:
            raise PayPalError("PayPal order ID verification failed.")

        capture = None

        for unit in result.get("purchase_units", []):
            for item in unit.get("payments", {}).get("captures", []):
                if item.get("status") == "COMPLETED":
                    capture = item
                    break

        if capture is None:
            raise PayPalError("No completed capture was returned by PayPal.")

        captured_amount = Decimal(
            str(capture.get("amount", {}).get("value", "0"))
        )
        captured_currency = capture.get("amount", {}).get("currency_code")

        if (
            captured_amount != Decimal(str(transaction.amount))
            or captured_currency != transaction.currency
        ):
            raise PayPalError("Captured amount or currency does not match the approved transaction.")

        transaction.paypal_capture_id = capture.get("id")
        transaction.status = "COMPLETED"
        transaction.raw_response = result

        procurement = db.session.get(
            ProcurementRequest,
            transaction.procurement_id,
        )
        if procurement:
            procurement.status = "PAID"

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "PayPal payment captured and verified.",
            "transaction_id": transaction.id,
            "paypal_order_id": transaction.paypal_order_id,
            "capture_id": transaction.paypal_capture_id,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status,
        }), 200

    except PayPalError as error:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": str(error),
        }), 502

    except Exception:
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "Unable to capture payment.",
        }), 500


@payments_bp.route(
    "/procurements/<int:procurement_id>/payments",
    methods=["GET"],
)
def payment_history(procurement_id):
    procurement = db.session.get(ProcurementRequest, procurement_id)

    if procurement is None:
        return jsonify({
            "success": False,
            "error": "Procurement not found.",
        }), 404

    transactions = PaymentTransaction.query.filter_by(
        procurement_id=procurement_id
    ).order_by(PaymentTransaction.created_at.desc()).all()

    return jsonify({
        "success": True,
        "payments": [
            {
                "id": item.id,
                "quote_id": item.quote_id,
                "paypal_order_id": item.paypal_order_id,
                "paypal_capture_id": item.paypal_capture_id,
                "amount": str(item.amount),
                "currency": item.currency,
                "status": item.status,
                "approval_confirmed": item.approval_confirmed,
                "created_at": item.created_at.isoformat(),
            }
            for item in transactions
        ],
    }), 200
