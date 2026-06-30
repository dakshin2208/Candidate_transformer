"""Unit tests — Output Projection Engine (doc 06 M6, doc 07 config-boundary)."""
import json
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from transformer.models import Config  # noqa: E402
from transformer.parsers import ATSParser, NotesParser  # noqa: E402
from transformer.matcher import match  # noqa: E402
from transformer.merge import merge  # noqa: E402
from transformer import conflict, provenance, confidence, canonical  # noqa: E402
from transformer.projection import project, MissingFieldError  # noqa: E402


def _build_profile():
    ats = ATSParser().parse((ROOT / "fixtures" / "ats.json").read_text())
    notes = NotesParser().parse((ROOT / "fixtures" / "recruiter-notes.txt").read_text())
    resolved = conflict.resolve(merge(match([ats, notes]))[0])
    return canonical.build(resolved, provenance.build(resolved), confidence.score(resolved))


def _cfg(mode):
    return Config.from_dict({"fields": [{"path": "ghost", "from": "does_not_exist"}],
                             "on_missing": mode, "include_provenance": False,
                             "include_confidence": False})


class TestProjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = _build_profile()

    def test_on_missing_null(self):
        out = project(self.profile, _cfg("null"))
        self.assertIn("ghost", out)
        self.assertIsNone(out["ghost"])

    def test_on_missing_omit(self):
        self.assertNotIn("ghost", project(self.profile, _cfg("omit")))

    def test_on_missing_error_raises(self):
        with self.assertRaises(MissingFieldError):
            project(self.profile, _cfg("error"))

    def test_from_path_remap(self):
        cfg = Config.from_dict({"fields": [{"path": "primary_email", "from": "emails[0]"}],
                                "on_missing": "omit", "include_provenance": False,
                                "include_confidence": False})
        self.assertEqual(project(self.profile, cfg), {"primary_email": "priya.sharma@gmail.com"})

    def test_config_boundary_profile_unchanged(self):
        """doc 07 config-boundary: projecting through two configs leaves the
        CanonicalProfile object byte-identical (projection is pure read-only)."""
        default_cfg = Config.from_dict(json.loads((ROOT / "configs" / "default-config.json").read_text()))
        custom_cfg = Config.from_dict(json.loads((ROOT / "configs" / "custom-config.json").read_text()))
        before = asdict(self.profile)
        out_default = project(self.profile, default_cfg)
        out_custom = project(self.profile, custom_cfg)
        self.assertNotEqual(set(out_default), set(out_custom))   # different shapes
        self.assertEqual(asdict(self.profile), before)            # profile unchanged


if __name__ == "__main__":
    unittest.main()
