"""Golden-file guarantee for the pure core (§8.3): fixed inputs → committed output, bit-stable."""

import json
from pathlib import Path

from backend.app.core.predict import predict
from tests.golden.inputs import golden_inputs

GOLDEN = Path(__file__).parent / "golden" / "predict_case.json"


def test_predict_matches_golden():
    battery, mode, zones, segments, stats = golden_inputs()
    out = predict(battery, mode, zones, segments, stats)
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert out == expected, "core/predict output drifted from the committed golden file"
