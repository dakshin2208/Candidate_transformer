"""Determinism tests (doc 07) — prove determinism, don't just claim it."""
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.models import Config  # noqa: E402
from transformer.pipeline import transform  # noqa: E402

ATS = ("ats", (ROOT / "fixtures" / "ats.json").read_text())
NOTES = ("notes", (ROOT / "fixtures" / "recruiter-notes.txt").read_text())
DEFAULT = Config.from_dict(json.loads((ROOT / "configs" / "default-config.json").read_text()))
CUSTOM = Config.from_dict(json.loads((ROOT / "configs" / "custom-config.json").read_text()))


def _run(sources, config):
    with contextlib.redirect_stderr(io.StringIO()):
        out, _ = transform(sources, config)
    return json.dumps(out, indent=2, sort_keys=False)  # byte-stable rendering


class TestDeterminism(unittest.TestCase):
    def test_repeat_run_stability(self):
        """N=5 identical runs -> byte-identical output."""
        outputs = {_run([ATS, NOTES], DEFAULT) for _ in range(5)}
        self.assertEqual(len(outputs), 1)

    def test_source_order_independence(self):
        """Shuffled source order -> identical output (final-tiebreak / no ordering leak)."""
        self.assertEqual(_run([ATS, NOTES], DEFAULT), _run([NOTES, ATS], DEFAULT))

    def test_order_independence_custom_config(self):
        self.assertEqual(_run([ATS, NOTES], CUSTOM), _run([NOTES, ATS], CUSTOM))


if __name__ == "__main__":
    unittest.main()
