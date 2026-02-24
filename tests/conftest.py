import uuid
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Merchant, Transaction, Chargeback

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def db_session():
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="session")
def client(setup_db, db_session):
    app.dependency_overrides[get_db] = override_get_db
    _seed_test_data(db_session)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_test_data(db):
    db.query(Chargeback).delete()
    db.query(Transaction).delete()
    db.query(Merchant).delete()
    db.commit()

    m1 = Merchant(id="merchant-high-1", name="High Ratio Merchant A", country="MX")
    m2 = Merchant(id="merchant-high-2", name="High Ratio Merchant B", country="CO")
    m3 = Merchant(id="merchant-clean-1", name="Clean Merchant C", country="CL")
    db.add_all([m1, m2, m3])
    db.commit()

    now = datetime(2024, 11, 15, 12, 0, 0)
    txs = []

    for i in range(80):
        txs.append(Transaction(
            id=f"tx-m1-{i}",
            timestamp=now - timedelta(days=i % 30),
            amount=500.0,
            currency="MXN",
            merchant_id="merchant-high-1",
            customer_id=f"cust-{i}",
            payment_method="credit_card",
            country="MX",
            product_category="Electronics",
            status="approved",
            card_bin="411111",
        ))

    for i in range(80):
        txs.append(Transaction(
            id=f"tx-m2-{i}",
            timestamp=now - timedelta(days=i % 30),
            amount=300000.0,
            currency="COP",
            merchant_id="merchant-high-2",
            customer_id=f"cust-co-{i}",
            payment_method="credit_card",
            country="CO",
            product_category="Apparel",
            status="approved",
            card_bin="524099",
        ))

    for i in range(100):
        txs.append(Transaction(
            id=f"tx-m3-{i}",
            timestamp=now - timedelta(days=i % 30),
            amount=50000.0,
            currency="CLP",
            merchant_id="merchant-clean-1",
            customer_id=f"cust-cl-{i}",
            payment_method="debit_card",
            country="CL",
            product_category="Groceries",
            status="approved",
            card_bin="601100",
        ))

    repeat_offender_id = "repeat-customer-001"
    for i in range(3):
        mid = ["merchant-high-1", "merchant-high-2", "merchant-clean-1"][i]
        txs.append(Transaction(
            id=f"tx-repeat-{i}",
            timestamp=now - timedelta(days=i),
            amount=800.0,
            currency="MXN",
            merchant_id=mid,
            customer_id=repeat_offender_id,
            payment_method="credit_card",
            country="MX",
            product_category="Electronics",
            status="approved",
            card_bin="411111",
        ))

    bin_anchor = datetime(2024, 11, 10, 10, 0, 0)
    high_value_bin = "999888"
    for i in range(3):
        txs.append(Transaction(
            id=f"tx-bin-{i}",
            timestamp=bin_anchor + timedelta(hours=i * 12),
            amount=1200.0,
            currency="MXN",
            merchant_id="merchant-high-1",
            customer_id=f"cust-bin-{i}",
            payment_method="credit_card",
            country="MX",
            product_category="Electronics",
            status="approved",
            card_bin=high_value_bin,
        ))

    db.add_all(txs)
    db.commit()

    cbs = []

    for i in range(10):
        cbs.append(Chargeback(
            id=f"cb-m1-{i}",
            transaction_id=f"tx-m1-{i}",
            chargeback_date=now - timedelta(days=i % 30) + timedelta(days=5),
            reason_code="10.4",
            reason_description="Card-Not-Present Fraud",
            status="open",
            amount=500.0,
        ))

    for i in range(10):
        cbs.append(Chargeback(
            id=f"cb-m2-{i}",
            transaction_id=f"tx-m2-{i}",
            chargeback_date=now - timedelta(days=i % 30) + timedelta(days=5),
            reason_code="13.1",
            reason_description="Merchandise/Services Not Received",
            status="open",
            amount=300000.0,
        ))

    for i in range(1):
        cbs.append(Chargeback(
            id=f"cb-m3-{i}",
            transaction_id=f"tx-m3-{i}",
            chargeback_date=now - timedelta(days=i % 30) + timedelta(days=5),
            reason_code="13.3",
            reason_description="Not as Described or Defective Merchandise",
            status="open",
            amount=50000.0,
        ))

    cbs.append(Chargeback(
        id="cb-m3-dup",
        transaction_id="tx-m3-1",
        chargeback_date=now + timedelta(days=5),
        reason_code="12.6",
        reason_description="Duplicate Processing",
        status="open",
        amount=50000.0,
    ))

    cbs.append(Chargeback(
        id="cb-m3-recurring",
        transaction_id="tx-m3-2",
        chargeback_date=now + timedelta(days=6),
        reason_code="13.2",
        reason_description="Cancelled Recurring Transaction",
        status="open",
        amount=50000.0,
    ))

    today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    spike_base = today - timedelta(days=3)
    spike_txs = []
    for i in range(20):
        tx_id = f"tx-spike-{i}"
        spike_txs.append(Transaction(
            id=tx_id,
            timestamp=spike_base - timedelta(hours=i),
            amount=200.0,
            currency="MXN",
            merchant_id="merchant-high-1",
            customer_id=f"cust-spike-{i}",
            payment_method="credit_card",
            country="MX",
            product_category="Digital Goods",
            status="approved",
            card_bin="411111",
        ))
        cbs.append(Chargeback(
            id=f"cb-spike-{i}",
            transaction_id=tx_id,
            chargeback_date=spike_base - timedelta(hours=i) + timedelta(days=1),
            reason_code="10.4",
            reason_description="Card-Not-Present Fraud",
            status="open",
            amount=200.0,
        ))

    prev_base = today - timedelta(days=10)
    prev_txs = []
    for i in range(3):
        tx_id = f"tx-prev-{i}"
        prev_txs.append(Transaction(
            id=tx_id,
            timestamp=prev_base - timedelta(hours=i),
            amount=200.0,
            currency="MXN",
            merchant_id="merchant-high-1",
            customer_id=f"cust-prev-{i}",
            payment_method="credit_card",
            country="MX",
            product_category="Digital Goods",
            status="approved",
            card_bin="411111",
        ))
        cbs.append(Chargeback(
            id=f"cb-prev-{i}",
            transaction_id=tx_id,
            chargeback_date=prev_base - timedelta(hours=i) + timedelta(days=1),
            reason_code="10.4",
            reason_description="Card-Not-Present Fraud",
            status="open",
            amount=200.0,
        ))

    db.add_all(spike_txs + prev_txs)
    db.commit()

    high_val_tx = Transaction(
        id="tx-high-value-1",
        timestamp=now,
        amount=10000.0,
        currency="MXN",
        merchant_id="merchant-high-1",
        customer_id="cust-hv-1",
        payment_method="credit_card",
        country="MX",
        product_category="Electronics",
        status="approved",
        card_bin="411111",
    )
    db.add(high_val_tx)
    db.commit()

    cbs.append(Chargeback(
        id="cb-high-value-1",
        transaction_id="tx-high-value-1",
        chargeback_date=now + timedelta(days=3),
        reason_code="10.4",
        reason_description="Card-Not-Present Fraud",
        status="open",
        amount=10000.0,
    ))

    for i in range(3):
        cbs.append(Chargeback(
            id=f"cb-repeat-{i}",
            transaction_id=f"tx-repeat-{i}",
            chargeback_date=now - timedelta(days=i) + timedelta(days=2),
            reason_code="10.4",
            reason_description="Card-Not-Present Fraud",
            status="open",
            amount=800.0,
        ))

    for i in range(3):
        cbs.append(Chargeback(
            id=f"cb-bin-{i}",
            transaction_id=f"tx-bin-{i}",
            chargeback_date=bin_anchor + timedelta(hours=i * 12) + timedelta(days=2),
            reason_code="10.4",
            reason_description="Card-Not-Present Fraud",
            status="open",
            amount=1200.0,
        ))

    db.add_all(cbs)
    db.commit()
