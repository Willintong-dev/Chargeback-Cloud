from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from app.database import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    country = Column(String, nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    merchant_id = Column(String, ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(String, nullable=False)
    payment_method = Column(String, nullable=False)
    country = Column(String, nullable=False)
    product_category = Column(String, nullable=False)
    status = Column(String, nullable=False)
    card_bin = Column(String(6), nullable=False)


class Chargeback(Base):
    __tablename__ = "chargebacks"

    id = Column(String, primary_key=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    chargeback_date = Column(DateTime, nullable=False)
    reason_code = Column(String, nullable=False)
    reason_description = Column(String, nullable=False)
    status = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
