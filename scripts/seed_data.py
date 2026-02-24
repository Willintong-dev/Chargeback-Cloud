import uuid
import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from app.models import Merchant, Transaction, Chargeback

fake = Faker()

COUNTRIES = ["MX", "CO", "CL"]
CURRENCIES = {"MX": "MXN", "CO": "COP", "CL": "CLP"}
PAYMENT_METHODS = ["credit_card", "debit_card", "local_payment"]
PAYMENT_METHOD_WEIGHTS = [0.60, 0.25, 0.15]
CATEGORIES = ["Electronics", "Apparel", "Home Goods", "Digital Goods", "Groceries", "Travel", "Beauty"]
STATUSES = ["approved", "declined", "pending"]
STATUS_WEIGHTS = [0.85, 0.10, 0.05]

REASON_CODES = {
    "10.4": "Card-Not-Present Fraud",
    "13.1": "Merchandise/Services Not Received",
    "13.3": "Not as Described or Defective Merchandise",
    "12.6": "Duplicate Processing",
    "13.2": "Cancelled Recurring Transaction",
}
REASON_CODE_WEIGHTS = [0.30, 0.35, 0.20, 0.08, 0.07]
REASON_CODE_LIST = list(REASON_CODES.keys())

CB_STATUSES = ["open", "won", "lost"]

START_DATE = datetime(2024, 10, 1)
END_DATE = datetime(2024, 12, 31)
BLACK_FRIDAY_START = datetime(2024, 11, 25)
BLACK_FRIDAY_END = datetime(2024, 12, 1)

REPEAT_OFFENDER_IDS = [str(uuid.uuid4()) for _ in range(5)]
HIGH_CB_BIN_PATTERNS = ["411111", "524099", "601100"]


def _random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def _amount_for_currency(currency: str) -> float:
    ranges = {"MXN": (200, 25000), "COP": (50000, 2000000), "CLP": (5000, 500000)}
    lo, hi = ranges[currency]
    return round(random.uniform(lo, hi), 2)


def run_seed(db: Session) -> dict:
    db.query(Chargeback).delete()
    db.query(Transaction).delete()
    db.query(Merchant).delete()
    db.commit()

    merchants = _create_merchants(db)
    transactions = _create_transactions(db, merchants)
    chargebacks = _create_chargebacks(db, transactions, merchants)

    return {
        "merchants": len(merchants),
        "transactions": len(transactions),
        "chargebacks": len(chargebacks),
    }


def _create_merchants(db: Session) -> list[Merchant]:
    merchants = []

    problem_merchants = [
        Merchant(id=str(uuid.uuid4()), name="TechZone Express MX", country="MX"),
        Merchant(id=str(uuid.uuid4()), name="Moda Rapida CO", country="CO"),
    ]

    clean_merchants = [
        Merchant(id=str(uuid.uuid4()), name=f"{fake.company()} {'MX' if i % 3 == 0 else 'CO' if i % 3 == 1 else 'CL'}", country=["MX", "CO", "CL"][i % 3])
        for i in range(10)
    ]

    all_merchants = problem_merchants + clean_merchants
    db.add_all(all_merchants)
    db.commit()
    merchants.extend(all_merchants)
    return merchants


def _create_transactions(db: Session, merchants: list[Merchant]) -> list[Transaction]:
    transactions = []
    problem_merchant_ids = {merchants[0].id, merchants[1].id}

    for merchant in merchants:
        count = 600 if merchant.id in problem_merchant_ids else 380
        for _ in range(count):
            country = merchant.country
            currency = CURRENCIES[country]
            ts = _random_date(START_DATE, END_DATE)
            customer_id = random.choice(REPEAT_OFFENDER_IDS) if random.random() < 0.04 else str(uuid.uuid4())
            payment_method = random.choices(PAYMENT_METHODS, PAYMENT_METHOD_WEIGHTS)[0]
            card_bin = (
                random.choice(HIGH_CB_BIN_PATTERNS)
                if payment_method == "credit_card" and random.random() < 0.06
                else fake.credit_card_number()[:6]
            )
            tx = Transaction(
                id=str(uuid.uuid4()),
                timestamp=ts,
                amount=_amount_for_currency(currency),
                currency=currency,
                merchant_id=merchant.id,
                customer_id=customer_id,
                payment_method=payment_method,
                country=country,
                product_category=random.choice(CATEGORIES),
                status=random.choices(STATUSES, STATUS_WEIGHTS)[0],
                card_bin=card_bin,
            )
            transactions.append(tx)

    db.add_all(transactions)
    db.commit()
    return transactions


def _create_chargebacks(db: Session, transactions: list[Transaction], merchants: list[Merchant]) -> list[Chargeback]:
    chargebacks = []
    problem_merchant_ids = {merchants[0].id, merchants[1].id}
    approved_txs = [t for t in transactions if t.status == "approved"]

    problem_txs = [t for t in approved_txs if t.merchant_id in problem_merchant_ids]
    clean_txs = [t for t in approved_txs if t.merchant_id not in problem_merchant_ids]

    problem_cb_count = int(len(problem_txs) * 0.08)
    clean_cb_count = int(len(clean_txs) * 0.020)

    problem_sample = random.sample(problem_txs, min(problem_cb_count, len(problem_txs)))
    clean_sample = random.sample(clean_txs, min(clean_cb_count, len(clean_txs)))

    selected_txs = problem_sample + clean_sample

    black_friday_txs = [
        t for t in approved_txs
        if BLACK_FRIDAY_START <= t.timestamp <= BLACK_FRIDAY_END
           and t not in selected_txs
    ]
    bf_extra = random.sample(black_friday_txs, min(int(len(black_friday_txs) * 0.12), len(black_friday_txs)))
    selected_txs = list(set(selected_txs + bf_extra))

    repeat_offender_txs = [
        t for t in approved_txs
        if t.customer_id in set(REPEAT_OFFENDER_IDS) and t not in selected_txs
    ]
    repeat_sample = random.sample(repeat_offender_txs, min(len(repeat_offender_txs), 5 * 3))
    selected_txs = list(set(selected_txs + repeat_sample))

    bin_txs_map: dict[str, list[Transaction]] = {}
    for t in approved_txs:
        if t.card_bin in HIGH_CB_BIN_PATTERNS:
            bin_txs_map.setdefault(t.card_bin, []).append(t)

    for bin_group in bin_txs_map.values():
        if len(bin_group) >= 3:
            anchor_time = _random_date(START_DATE, END_DATE - timedelta(days=2))
            anchored = [
                t for t in bin_group
                if abs((t.timestamp - anchor_time).total_seconds()) <= 48 * 3600
            ]
            if len(anchored) < 3:
                anchored = bin_group[:3]
            for t in anchored:
                if t not in selected_txs:
                    selected_txs.append(t)

    reason_code_keys = list(REASON_CODES.keys())
    for tx in selected_txs:
        reason_code = random.choices(reason_code_keys, REASON_CODE_WEIGHTS)[0]
        cb_date = tx.timestamp + timedelta(days=random.randint(1, 45))
        cb = Chargeback(
            id=str(uuid.uuid4()),
            transaction_id=tx.id,
            chargeback_date=cb_date,
            reason_code=reason_code,
            reason_description=REASON_CODES[reason_code],
            status=random.choice(CB_STATUSES),
            amount=tx.amount,
        )
        chargebacks.append(cb)

    db.add_all(chargebacks)
    db.commit()
    return chargebacks
