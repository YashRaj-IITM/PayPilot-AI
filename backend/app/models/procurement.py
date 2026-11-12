from datetime import datetime, timezone
from app import db


def utc_now():
    return datetime.now(timezone.utc)


class ProcurementRequest(db.Model):
    __tablename__ = "procurement_requests"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)

    budget_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")

    status = db.Column(
        db.String(30),
        nullable=False,
        default="DRAFT"
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

    quotes = db.relationship(
        "SupplierQuote",
        backref="procurement",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "budget_amount": str(self.budget_amount),
            "currency": self.currency,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "quotes": [quote.to_dict() for quote in self.quotes]
        }


class SupplierQuote(db.Model):
    __tablename__ = "supplier_quotes"

    id = db.Column(db.Integer, primary_key=True)

    procurement_id = db.Column(
        db.Integer,
        db.ForeignKey("procurement_requests.id"),
        nullable=False
    )

    supplier_name = db.Column(
        db.String(150),
        nullable=False
    )

    item_description = db.Column(db.Text, nullable=False)

    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    total_price = db.Column(db.Numeric(12, 2), nullable=False)

    delivery_days = db.Column(db.Integer, nullable=True)
    source_url = db.Column(db.String(500), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "procurement_id": self.procurement_id,
            "supplier_name": self.supplier_name,
            "item_description": self.item_description,
            "unit_price": str(self.unit_price),
            "quantity": self.quantity,
            "total_price": str(self.total_price),
            "delivery_days": self.delivery_days,
            "source_url": self.source_url
        }


class AIAnalysis(db.Model):
    __tablename__ = "ai_analyses"

    id = db.Column(db.Integer, primary_key=True)

    procurement_id = db.Column(
        db.Integer,
        db.ForeignKey("procurement_requests.id"),
        nullable=False
    )

    provider = db.Column(db.String(80), nullable=False)
    model = db.Column(db.String(120), nullable=False)

    summary = db.Column(db.Text, nullable=False)
    analysis_json = db.Column(db.JSON, nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )


class PaymentTransaction(db.Model):
    __tablename__ = "payment_transactions"

    id = db.Column(db.Integer, primary_key=True)

    procurement_id = db.Column(
        db.Integer,
        db.ForeignKey("procurement_requests.id"),
        nullable=False
    )

    quote_id = db.Column(
        db.Integer,
        db.ForeignKey("supplier_quotes.id"),
        nullable=False
    )

    paypal_order_id = db.Column(
        db.String(100),
        unique=True,
        nullable=True
    )

    paypal_capture_id = db.Column(
        db.String(100),
        nullable=True
    )

    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False)

    status = db.Column(
        db.String(30),
        nullable=False,
        default="CREATED"
    )

    approval_confirmed = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    raw_response = db.Column(db.JSON, nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )
