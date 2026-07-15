"""API layer (§6) against a small seeded DB, plus generator determinism (§12.2)."""

import pytest
from fastapi.testclient import TestClient

from backend.app import config
from backend.app.api import routes
from backend.app.main import app
from simulator.generate import build_db, canonical_hash


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    build_db(db_path, seed=7, n_sessions=12)
    original = config.DB_PATH
    config.DB_PATH = db_path
    routes._Db.reset()
    with TestClient(app) as c:
        yield c
    config.DB_PATH = original
    routes._Db.reset()


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["engine"] == "rule_v1"


def test_predict_shape(client):
    r = client.get("/api/predict", params={"battery": 55, "mode": "standard"})
    assert r.status_code == 200
    body = r.json()
    for key in (
        "engine",
        "t_est_min",
        "t_lo_min",
        "t_hi_min",
        "t_req_min",
        "p_complete",
        "state",
        "per_mode",
        "basis",
    ):
        assert key in body
    assert set(body["per_mode"]) == set(config.MODES)
    assert body["basis"]["interval_method"] == "joint_weighted_bootstrap"


def test_predict_zone_subset_lowers_t_req(client):
    full = client.get("/api/predict", params={"battery": 55}).json()
    part = client.get("/api/predict", params={"battery": 55, "zones": "1"}).json()
    assert part["t_req_min"] < full["t_req_min"]


def test_error_shape_on_bad_mode(client):
    r = client.get("/api/predict", params={"battery": 55, "mode": "hyper"})
    assert r.status_code == 400
    assert set(r.json()["error"]) == {"code", "message"}


def test_unknown_zone_rejected(client):
    r = client.get("/api/predict", params={"battery": 55, "zones": "1,99"})
    assert r.status_code == 400


def test_sessions_listing(client):
    body = client.get("/api/sessions").json()
    assert len(body) == 12
    assert body[0]["started_at"] >= body[-1]["started_at"]  # newest first


def test_generator_is_deterministic(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    build_db(a, seed=7, n_sessions=6)
    build_db(b, seed=7, n_sessions=6)
    assert canonical_hash(a) == canonical_hash(b)
    build_db(b, seed=8, n_sessions=6)
    assert canonical_hash(a) != canonical_hash(b)
