"""Regenerate the committed golden files after an INTENTIONAL core/physics change.

  python -m tests.golden.regen

Review the diff before committing — a golden change is a behavior change.
"""

import json
from pathlib import Path

import numpy as np

from backend.app import config
from backend.app.core.predict import predict
from simulator.battery import BatteryModel, suction_power_w

from .inputs import golden_inputs

HERE = Path(__file__).parent


def regen_predict() -> None:
    battery, mode, zones, segments, stats = golden_inputs()
    out = predict(battery, mode, zones, segments, stats)
    (HERE / "predict_case.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def regen_discharge() -> None:
    rng = np.random.default_rng(config.DEMO_SEED)
    model = BatteryModel(rng)
    power = suction_power_w("standard", False, 50.0, 0.0)
    battery, curve = 100.0, [100.0]
    for _ in range(30):
        battery -= model.step_dsoc(power)
        curve.append(round(battery, 4))
    (HERE / "discharge_curve.json").write_text(json.dumps(curve) + "\n", encoding="utf-8")


if __name__ == "__main__":
    regen_predict()
    regen_discharge()
    print("golden files regenerated under tests/golden/")
