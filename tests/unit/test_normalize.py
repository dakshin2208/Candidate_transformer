"""Unit tests — Normalization Engine (doc 04, doc 07)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from transformer.normalize import (  # noqa: E402
    normalize_company, normalize_country, normalize_date, normalize_email,
    normalize_name, normalize_phone, normalize_skill,
)

ALL = [normalize_email, normalize_phone, normalize_date, normalize_country,
       normalize_skill, normalize_name, normalize_company]


class TestEmail(unittest.TestCase):
    def test_mixed_case_and_whitespace(self):
        self.assertEqual(normalize_email("  Priya.Sharma@Gmail.com "), "priya.sharma@gmail.com")

    def test_non_email_is_none(self):
        self.assertIsNone(normalize_email("not-an-email"))
        self.assertIsNone(normalize_email("   "))


class TestPhone(unittest.TestCase):
    def test_parenthesised_nanp(self):
        self.assertEqual(normalize_phone("(415) 555-0142"), "+14155550142")

    def test_plus_one_form(self):
        self.assertEqual(normalize_phone("+1 415-555-0142"), "+14155550142")

    def test_garbage_is_none(self):
        self.assertIsNone(normalize_phone("abc"))
        self.assertIsNone(normalize_phone("12345"))


class TestDate(unittest.TestCase):
    def test_yyyy_mm_passthrough(self):
        self.assertEqual(normalize_date("2022-03"), "2022-03")

    def test_year_only_is_none(self):
        self.assertIsNone(normalize_date("2019"))

    def test_impossible_month_is_none(self):
        self.assertIsNone(normalize_date("2022-13"))


class TestCountry(unittest.TestCase):
    def test_united_states(self):
        self.assertEqual(normalize_country("United States"), "US")

    def test_india(self):
        self.assertEqual(normalize_country("India"), "IN")

    def test_unknown_is_none(self):
        self.assertIsNone(normalize_country("Atlantis"))


class TestSkill(unittest.TestCase):
    def test_alias_js(self):
        self.assertEqual(normalize_skill("JS"), "JavaScript")

    def test_alias_k8s(self):
        self.assertEqual(normalize_skill("K8s"), "Kubernetes")

    def test_unknown_preserved(self):
        self.assertEqual(normalize_skill("SomeNicheTool"), "SomeNicheTool")


class TestNameAndCompany(unittest.TestCase):
    def test_name_collapses_whitespace(self):
        self.assertEqual(normalize_name("  Priya   Sharma "), "Priya Sharma")

    def test_company_casing(self):
        self.assertEqual(normalize_company("GOOGLE"), "Google")
        self.assertEqual(normalize_company("eBay"), "eBay")  # brand casing preserved


class TestNeverRaises(unittest.TestCase):
    def test_all_normalizers_survive_garbage(self):
        garbage = [None, "", "   ", 123, 3.14, [], {}, "\n\t"]
        for fn in ALL:
            for g in garbage:
                with self.subTest(fn=fn.__name__, value=g):
                    try:
                        fn(g)  # must not raise
                    except Exception as exc:  # noqa: BLE001
                        self.fail(f"{fn.__name__}({g!r}) raised {exc!r}")


if __name__ == "__main__":
    unittest.main()
