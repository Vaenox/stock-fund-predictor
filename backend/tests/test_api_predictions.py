from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db
from app.models.market_data import Asset, AssetStatus, AssetType
from app.models.prediction_history import PredictionHistory


ASSET_ID = uuid4()
GENERATED_AT = datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc)


def _asset() -> Asset:
    return Asset(
        id=ASSET_ID,
        asset_type=AssetType.STOCK,
        canonical_symbol="THYAO",
        name="Türk Hava Yolları",
        isin=None,
        exchange="BIST",
        currency="TRY",
        status=AssetStatus.ACTIVE,
    )


def _prediction() -> PredictionHistory:
    return PredictionHistory(
        id=uuid4(),
        asset_id=ASSET_ID,
        prediction_date=date(2026, 10, 6),
        generated_at=GENERATED_AT,
        data_as_of=date(2026, 10, 6),
        horizon_days=5,
        target_return_threshold=Decimal("0.03"),
        model_family="xgboost",
        model_version="test-v1",
        feature_representation="raw_all",
        ml_probability=Decimal("0.62"),
        technical_score=Decimal("71.5"),
        risk_score=Decimal("24"),
        risk_adjustment=Decimal("-4.8"),
        signal_score=Decimal("61.7"),
        target_weight=Decimal("0.617"),
        quality_ok=True,
        stale_days=0,
        source_provider="borsapy",
        reasons=["Trend olumlu"],
    )


class FakeResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeSession:
    def __init__(self, asset, predictions):
        self.asset = asset
        self.predictions = predictions

    def scalar(self, _statement):
        if "prediction_history" in str(_statement):
            return self.predictions[0] if self.predictions else None
        return self.asset

    def scalars(self, _statement):
        return FakeResult(self.predictions)


def _client(asset=None, predictions=None):
    fake = FakeSession(asset or _asset(), predictions if predictions is not None else [_prediction()])

    def override_get_db():
        yield fake

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_asset_normalizes_symbol():
    client = _client()
    response = client.get("/api/v1/assets/thyao")

    assert response.status_code == 200
    body = response.json()
    assert body["canonical_symbol"] == "THYAO"
    assert body["asset_type"] == "STOCK"


def test_get_latest_prediction_returns_persisted_fields():
    client = _client()
    response = client.get("/api/v1/assets/THYAO/predictions/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["prediction_date"] == "2026-10-06"
    assert body["source_provider"] == "borsapy"
    assert body["model_family"] == "xgboost"
    assert body["target_weight"] == 0.617
    assert body["reasons"] == ["Trend olumlu"]


def test_list_prediction_history_supports_date_filters_and_pagination():
    prediction = _prediction()
    client = _client(predictions=[prediction])

    response = client.get(
        "/api/v1/assets/THYAO/predictions"
        "?start_date=2026-10-01&end_date=2026-10-06&limit=50&offset=0"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == str(prediction.id)


def test_asset_not_found_is_404():
    client = _client(asset=None)
    fake = FakeSession(None, [_prediction()])

    def override_get_db():
        yield fake

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/api/v1/assets/UNKNOWN")
    assert response.status_code == 404


def test_latest_prediction_not_found_is_404():
    client = _client(predictions=[])
    response = client.get("/api/v1/assets/THYAO/predictions/latest")
    assert response.status_code == 404


def test_prediction_date_range_rejects_reversed_dates():
    client = _client()
    response = client.get(
        "/api/v1/assets/THYAO/predictions"
        "?start_date=2026-10-07&end_date=2026-10-06"
    )
    assert response.status_code == 400
