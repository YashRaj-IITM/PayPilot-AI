from flask import Blueprint, jsonify

from app import db
from app.models.procurement import ProcurementRequest, AIAnalysis
from app.services.procurement_intelligence import analyze_procurement

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route(
    "/procurements/<int:procurement_id>/analyze",
    methods=["POST"]
)
def analyze(procurement_id):
    procurement = db.session.get(
        ProcurementRequest, procurement_id
    )

    if procurement is None:
        return jsonify({
            "success": False,
            "error": "Procurement request not found."
        }), 404

    try:
        result = analyze_procurement(procurement)

        record = AIAnalysis(
            procurement_id=procurement.id,
            provider="paypilot_rules_engine",
            model="procurement-scoring-v1",
            summary="Explainable supplier ranking generated from submitted quotations.",
            analysis_json=result
        )

        procurement.status = "ANALYZED"

        db.session.add(record)
        db.session.commit()

        return jsonify({
            "success": True,
            "analysis": result
        }), 200

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
            "error": "Unable to analyze procurement."
        }), 500
