"""Offline checks; never imports application/DB fixtures or connects to MySQL."""
import copy
from datetime import date
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import shutil

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("market_prices", ROOT / "scripts/update_market_prices.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SOURCE = ROOT / "app/db/seed_data/market_prices_20261029.json"


class PricesTest(unittest.TestCase):
    def test_complete_catalog_and_package_dimensions(self):
        data = module.load_prices(SOURCE.parent / "budget_prices_20261101.json", date(2026, 11, 1))
        by_id = {e["ingredient_id"]: e for e in data["entries"]}
        self.assertEqual(len(by_id), 132)
        self.assertEqual(sum(e["price_reference"]["status"] == "estimated" for e in by_id.values()), 99)
        self.assertEqual((by_id[56]["unit"], by_id[56]["unit_price"]), ("升", "2.27"))
        self.assertEqual((by_id[35]["unit"], by_id[35]["unit_price"]), ("升", "105.33"))
        self.assertEqual((by_id[109]["unit"], by_id[109]["unit_price"]), ("斤", "72.00"))
        self.assertEqual((by_id[43]["unit"], by_id[43]["unit_price"]), ("斤", "4.95"))
        self.assertEqual(by_id[92]["price_reference"]["source_ids"], [])
        self.assertEqual(by_id[9]["price_reference"]["anchors"][0]["published_on"], "2025-03-04")

    def test_metadata_only_update_preserves_other_fields_and_is_idempotent(self):
        entry = {"ingredient_id": 1, "unit": "斤", "unit_price": "4.32", "price_reference": {"status": "estimated"}}
        raw = '[ {"ingredient_id":1,"unit":"斤","unit_price":4.32,"name":"番茄"} ]'.encode("utf-8")
        updated = module.update_seed_text(raw, [entry])
        self.assertEqual(json.loads(updated)[0]["price_reference"], entry["price_reference"])
        self.assertEqual(module.update_seed_text(updated, [entry]), updated)
        entry["price_reference"] = {"status": "observed"}
        changed = module.update_seed_text(updated, [entry])
        self.assertEqual(json.loads(changed)[0]["price_reference"], entry["price_reference"])

    def test_estimates_cannot_be_mislabeled_or_cross_dimensions(self):
        original = json.loads((SOURCE.parent / "budget_prices_20261101.json").read_text(encoding="utf-8"))
        cases = []
        for mutation in ("status", "dimension", "price", "source", "reviewed"):
            data = copy.deepcopy(original)
            entry = next(e for e in data["entries"] if e["ingredient_id"] == 35)
            if mutation == "status": entry["price_reference"]["status"] = "observed"
            if mutation == "dimension": entry["price_reference"]["planning_package"]["measure"] = "g"
            if mutation == "price": entry["unit_price"] = "79.00"
            if mutation == "source": entry["price_reference"]["anchors"] = [{"publisher": "fake retailer"}]
            if mutation == "reviewed": data["entries"][0]["unit_price"] = "9.99"
            cases.append(data)
        with TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "reference").mkdir()
            shutil.copyfile(SOURCE, target / SOURCE.name)
            shutil.copyfile(SOURCE.parent / "reference/shanghai-prices-20261029.xls", target / "reference/shanghai-prices-20261029.xls")
            for data in cases:
                path = target / "bundle.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    module.load_prices(path, date(2026, 11, 1))

    def test_seed_format_and_unselected_fields_are_preserved(self):
        raw = '[\n  {"ingredient_id":1,"unit":"个","unit_price":2.5,"name":"番茄"},\n  {"ingredient_id":3,"unit":"斤","unit_price":15.0}\n]\n'.encode("utf-8")
        updated = module.update_seed_text(raw, [{"ingredient_id": 1, "unit": "斤", "unit_price": "4.32"}])
        self.assertEqual(updated.decode("utf-8"), raw.decode("utf-8").replace('"unit":"个","unit_price":2.5', '"unit":"斤","unit_price":4.32'))
        self.assertEqual(module.update_seed_text(updated, [{"ingredient_id": 1, "unit": "斤", "unit_price": "4.32"}]), updated)

    def test_original_evidence_and_all_prices(self):
        data = module.load_prices(SOURCE, date(2026, 11, 1))
        self.assertEqual(len(data["entries"]), 33)
        tomato = next(e for e in data["entries"] if e["name"] == "番茄")
        self.assertEqual(tomato["unit_price"], "4.32")
        # 4.32 yuan/500g => 2.16 yuan/250g, not 1080 yuan.
        from decimal import Decimal
        self.assertEqual(Decimal(tomato["unit_price"]) * Decimal(250) / 500, Decimal("2.16"))
        self.assertTrue({"鸡胸肉", "虾仁", "鳕鱼", "彩椒", "牛奶", "花生油"}.isdisjoint({e["name"] for e in data["entries"]}))

    def test_future_or_expired_quote_rejected(self):
        for today in (date(2026, 10, 28), date(2026, 11, 29)):
            with self.assertRaises(ValueError):
                module.load_prices(SOURCE, today)

    def test_bad_unit_weight_duplicate_and_transcription_rejected(self):
        original = json.loads(SOURCE.read_text(encoding="utf-8"))
        cases = []
        for key, value in [("unit", "个"), ("quoted_weight_g", 1000), ("unit_price", "0.43"), ("quoted_price_cny", "999"), ("source_name", "鸡胸肉"), ("specification", "去骨")]:
            data = copy.deepcopy(original)
            data["entries"][0][key] = value
            cases.append(data)
        duplicate = copy.deepcopy(original)
        duplicate["entries"].append(duplicate["entries"][0])
        cases.append(duplicate)
        with TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "reference").mkdir()
            shutil.copyfile(SOURCE.parent / "reference/shanghai-prices-20261029.xls", target / "reference/shanghai-prices-20261029.xls")
            for data in cases:
                path = target / "bundle.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    module.load_prices(path, date(2026, 11, 1))


if __name__ == "__main__":
    unittest.main()
