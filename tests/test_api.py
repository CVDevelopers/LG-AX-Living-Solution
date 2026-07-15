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


def test_heatmap_shape_and_bounds(client):
    hm = client.get("/api/heatmap", params={"battery": 40, "mode": "standard"}).json()
    assert len(hm["grid"]) > 0 and len(hm["grid"][0]) > 0
    assert hm["cells"] and all(0.0 <= c["p"] <= 1.0 for c in hm["cells"])
    orders = [z["order"] for z in hm["zones"]]
    assert orders == list(range(1, len(orders) + 1))  # 1..n visit order, contiguous
    assert 3.0 <= hm["b_res"] <= 8.0  # dynamic reserve clamp (§3.2)


@pytest.mark.parametrize("battery", [80, 55, 40, 18])
@pytest.mark.parametrize("mode", ["eco", "standard", "turbo"])
def test_heatmap_matches_banner_probability(client, battery, mode):
    """M1 DoD — heatmap and banner never disagree: both are one distribution (§1 principle 7)."""
    pred = client.get("/api/predict", params={"battery": battery, "mode": mode}).json()
    hm = client.get("/api/heatmap", params={"battery": battery, "mode": mode}).json()
    whole_plan_p = hm["zones"][-1]["p_complete"]  # last zone in visit order = finish everything
    assert abs(whole_plan_p - pred["p_complete"]) <= 0.02


def test_heatmap_zone_completion_non_increasing_along_route(client):
    hm = client.get("/api/heatmap", params={"battery": 40, "mode": "standard"}).json()
    ps = [z["p_complete"] for z in hm["zones"]]
    assert ps == sorted(ps, reverse=True)


def test_shortage_a_at_18pct_offers_feasible_subset(client):
    """M1 DoD demo scenario: at 18 % battery the banner is 부족A and a subset still completes."""
    pred = client.get("/api/predict", params={"battery": 18, "mode": "standard"}).json()
    assert pred["state"] == "shortage_a"
    body = client.post("/api/plan", json={"battery": 18}).json()
    assert body["feasible"] is True
    plan = body["plan"]
    assert plan["p_complete"] >= 0.90 - 1e-9
    assert 1 <= len(plan["zone_ids"]) <= len(pred["per_mode"]) + 5  # a non-empty subset
    assert [z["order"] for z in plan["zones"]] == list(range(1, len(plan["zones"]) + 1))


def test_plan_below_budget_is_infeasible(client):
    body = client.post("/api/plan", json={"battery": 6}).json()
    assert body["feasible"] is False and body["plan"] is None
    assert client.get("/api/predict", params={"battery": 6}).json()["state"] == "shortage_b"


def test_next_plan_roundtrip(client):
    assert client.get("/api/next-plan").json()["next_plan"] is None
    created = client.post("/api/next-plan", json={"zone_ids": [2, 3], "mode": "eco"}).json()
    assert created["ok"] is True
    got = client.get("/api/next-plan").json()["next_plan"]
    assert got["zone_ids"] == [2, 3] and got["mode"] == "eco"
    assert client.post(f"/api/next-plan/{created['plan_id']}/consume").json()["ok"] is True
    assert client.get("/api/next-plan").json()["next_plan"] is None


def test_generator_is_deterministic(tmp_path):
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    build_db(a, seed=7, n_sessions=6)
    build_db(b, seed=7, n_sessions=6)
    assert canonical_hash(a) == canonical_hash(b)
    build_db(b, seed=8, n_sessions=6)
    assert canonical_hash(a) != canonical_hash(b)
