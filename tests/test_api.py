import pytest


def test_seed_loads_data():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    from scripts.seed_data import run_seed

    seed_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=seed_engine)
    SeedSession = sessionmaker(bind=seed_engine)
    db = SeedSession()
    result = run_seed(db)
    db.close()

    assert result["transactions"] >= 5000
    assert result["chargebacks"] >= 200


def test_merchant_ratio_returns_all_merchants(client):
    response = client.get("/api/merchants/chargeback-ratio")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3
    for item in data:
        assert "merchant_id" in item
        assert "name" in item
        assert "chargeback_ratio" in item


def test_merchant_ratio_sorted_desc(client):
    response = client.get("/api/merchants/chargeback-ratio")
    assert response.status_code == 200
    ratios = [item["chargeback_ratio"] for item in response.json()]
    assert ratios == sorted(ratios, reverse=True)


def test_reason_codes_all_codes_present(client):
    response = client.get("/api/reason-codes")
    assert response.status_code == 200
    codes = {item["reason_code"] for item in response.json()}
    expected = {"10.4", "13.1", "13.3", "12.6", "13.2"}
    assert expected.issubset(codes)


def test_segments_threshold_filter(client):
    threshold = 1.5
    response = client.get(f"/api/segments/high-risk?dimension=country&threshold={threshold}")
    assert response.status_code == 200
    for item in response.json():
        assert item["chargeback_ratio"] > threshold


def test_segments_invalid_dimension(client):
    response = client.get("/api/segments/high-risk?dimension=invalid")
    assert response.status_code == 400


def test_trends_daily_granularity(client):
    response = client.get("/api/trends?granularity=daily")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    periods = [item["period"] for item in data]
    assert len(periods) == len(set(periods))
    for item in data:
        assert item["chargeback_count"] > 0


def test_trends_weekly_granularity(client):
    response = client.get("/api/trends?granularity=weekly")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    periods = [item["period"] for item in data]
    assert len(periods) == len(set(periods))


def test_trends_invalid_granularity(client):
    response = client.get("/api/trends?granularity=monthly")
    assert response.status_code == 400


def test_alerts_high_ratio_merchant(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    high_ratio_alerts = [
        a for a in response.json()
        if a["alert_type"] == "HIGH_CHARGEBACK_RATIO" and a["severity"] == "HIGH"
    ]
    assert len(high_ratio_alerts) >= 2


def test_alerts_spike_detection(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    spike_alerts = [
        a for a in response.json()
        if a["alert_type"] == "WEEKLY_SPIKE"
    ]
    assert len(spike_alerts) >= 1


def test_alerts_high_value_disputes(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    hv_alerts = [
        a for a in response.json()
        if a["alert_type"] == "HIGH_VALUE_DISPUTE" and a["severity"] == "HIGH"
    ]
    assert len(hv_alerts) >= 1
    for alert in hv_alerts:
        assert alert["metric_value"] > 500


def test_fraud_patterns_same_customer(client):
    response = client.get("/api/fraud-patterns")
    assert response.status_code == 200
    repeat_offenders = [
        p for p in response.json()
        if p["pattern_type"] == "REPEAT_OFFENDER"
    ]
    assert len(repeat_offenders) >= 1
    for offender in repeat_offenders:
        assert offender["chargeback_count"] >= 3


def test_fraud_patterns_same_bin(client):
    response = client.get("/api/fraud-patterns")
    assert response.status_code == 200
    bin_patterns = [
        p for p in response.json()
        if p["pattern_type"] == "BIN_PATTERN"
    ]
    assert len(bin_patterns) >= 1
    for pattern in bin_patterns:
        assert pattern["chargeback_count"] >= 2
        assert pattern["time_window_hours"] == 48


def test_win_rate_all_codes_present(client):
    response = client.get("/api/win-rate")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    for item in data:
        assert "reason_code" in item
        assert "win_rate" in item
        assert "won" in item
        assert "lost" in item
        assert "open" in item
        assert 0.0 <= item["win_rate"] <= 100.0


def test_win_rate_excludes_open_from_denominator(client):
    response = client.get("/api/win-rate")
    assert response.status_code == 200
    for item in response.json():
        resolved = item["won"] + item["lost"]
        if resolved > 0:
            expected_rate = round(item["won"] / resolved * 100, 2)
            assert abs(item["win_rate"] - expected_rate) < 0.1


def test_recommendations_returns_one_per_merchant(client):
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    merchant_ids = [item["merchant_id"] for item in data]
    assert len(merchant_ids) == len(set(merchant_ids))


def test_recommendations_dominant_code_and_text(client):
    response = client.get("/api/recommendations")
    assert response.status_code == 200
    for item in response.json():
        assert item["dominant_reason_code"] in {"10.4", "13.1", "13.3", "12.6", "13.2"}
        assert len(item["recommendation"]) > 10


def test_alerts_configurable_threshold(client):
    response_tight = client.get("/api/alerts?ratio_threshold=0.1")
    response_loose = client.get("/api/alerts?ratio_threshold=99.0")
    assert response_tight.status_code == 200
    assert response_loose.status_code == 200
    tight_count = sum(1 for a in response_tight.json() if a["alert_type"] == "HIGH_CHARGEBACK_RATIO")
    loose_count = sum(1 for a in response_loose.json() if a["alert_type"] == "HIGH_CHARGEBACK_RATIO")
    assert tight_count >= loose_count
