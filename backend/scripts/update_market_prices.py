"""Preview/apply reviewed retail quotes. Never infer a piece or package weight."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys


def update_seed_text(raw: bytes, entries: list[dict]) -> bytes:
    """Preserve unrelated records and existing compact/expanded formatting."""
    text = raw.decode("utf-8")
    decoder = json.JSONDecoder()
    edits = []
    selected = {entry["ingredient_id"]: entry for entry in entries}
    pos = text.index("[") + 1
    while True:
        while text[pos].isspace() or text[pos] == ",":
            pos += 1
        if text[pos] == "]":
            break
        row, end = decoder.raw_decode(text, pos)
        entry = selected.get(row["ingredient_id"])
        if entry and (row["unit"] != entry["unit"] or Decimal(str(row["unit_price"])) != Decimal(entry["unit_price"])):
            fragment = text[pos:end]
            fragment, count_unit = re.subn(r'("unit"\s*:\s*)"[^"\\]*"', lambda match: match[1] + json.dumps(entry["unit"], ensure_ascii=False), fragment)
            fragment, count_price = re.subn(r'("unit_price"\s*:\s*)-?\d+(?:\.\d+)?', lambda match: match[1] + entry["unit_price"], fragment)
            if count_unit != 1 or count_price != 1:
                raise ValueError("种子文件字段格式异常")
            edits.append((pos, end, fragment))
        pos = end
    for start, end, value in reversed(edits):
        text = text[:start] + value + text[end:]
    return text.encode("utf-8")


def load_prices(path: Path, as_of: date) -> dict:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    observed = date.fromisoformat(bundle["observed_on"])
    expiry = date.fromisoformat(bundle["valid_through"])
    if not observed <= as_of <= expiry or not 0 <= (expiry - observed).days <= 31:
        raise ValueError("价格不在有效期内，需重新核对行情")
    if not bundle["url"].startswith("https://") or len(bundle["attachment_sha256"]) != 64:
        raise ValueError("来源证据缺失")
    evidence_path = path.parent / "reference/shanghai-prices-20261029.xls"
    evidence = evidence_path.read_bytes()
    if hashlib.sha256(evidence).hexdigest() != bundle["attachment_sha256"]:
        raise ValueError("原始附件摘要不匹配")
    import xlrd
    sheet = xlrd.open_workbook(file_contents=evidence).sheet_by_index(0)
    if sheet.cell_value(2, 0) != "采价时间：" + observed.strftime("%Y年%m月%d日"):
        raise ValueError("原始附件采价日期不匹配")
    ids = set()
    for entry in bundle["entries"]:
        if entry["ingredient_id"] in ids:
            raise ValueError("重复食材")
        ids.add(entry["ingredient_id"])
        # Original schema has only two decimals. Store per 斤, not per gram.
        if entry["unit"] != "斤" or entry["source_unit"] != "元/500克":
            raise ValueError("此导入器只接受重量明确的元/500克报价")
        weight = Decimal(str(entry["quoted_weight_g"]))
        quote = Decimal(entry["quoted_price_cny"])
        price = Decimal(entry["unit_price"])
        if weight != 500 or not quote.is_finite() or quote <= 0:
            raise ValueError("重量或报价错误")
        expected = (quote * Decimal(500) / weight).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        if not price.is_finite() or price != expected or price <= 0:
            raise ValueError("价格与重量不对应")
        col = entry["source_column_index"]
        if (sheet.cell_value(4, col) != entry["source_name"]
                or sheet.cell_value(5, col) != entry["specification"]
                or sheet.cell_value(6, col) != entry["source_unit"]
                or Decimal(str(sheet.cell_value(7, col))) != quote):
            raise ValueError("原表品种、规格、计价单位或报价不匹配")
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    backend = Path(__file__).resolve().parents[1]
    bundle = load_prices(args.file, args.as_of)
    from dotenv import dotenv_values
    import pymysql

    env = dotenv_values(backend / ".env")
    if env.get("DATABASE_URL_OVERRIDE") or env.get("DB_NAME", "nutrigenie") != "nutrigenie" or env.get("DB_HOST", "localhost") not in ("localhost", "127.0.0.1"):
        raise ValueError("本次工具仅针对已核对的本机 nutrigenie 库")
    db = pymysql.connect(host=env.get("DB_HOST", "localhost"), port=int(env.get("DB_PORT", 3306)), user=env.get("DB_USER", "root"), password=env.get("DB_PASSWORD", ""), database="nutrigenie", charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor, connect_timeout=5)
    seed_path = backend / "app/db/seed_data/ingredients.json"
    seed_before = seed_path.read_bytes()
    seed = json.loads(seed_before)
    by_id = {row["ingredient_id"]: row for row in seed}
    changed_seed = False
    committed = False
    backup = None
    try:
        db.begin()
        with db.cursor() as cur:
            cur.execute("SELECT ingredient_id,name,unit,unit_price FROM ingredients ORDER BY ingredient_id" + (" FOR UPDATE" if args.apply else ""))
            rows = cur.fetchall()
            existing = {row["ingredient_id"]: row for row in rows}
            changes = []
            for entry in bundle["entries"]:
                old = existing[entry["ingredient_id"]]
                if old["name"] != entry["name"] or by_id[entry["ingredient_id"]]["name"] != entry["name"]:
                    raise ValueError("食材编号与名称不符，拒绝更新")
                if old["unit"] != entry["unit"] or old["unit_price"] != Decimal(entry["unit_price"]):
                    changes.append({"before": old, "after": {"ingredient_id": entry["ingredient_id"], "name": entry["name"], "unit": entry["unit"], "unit_price": entry["unit_price"]}})
                by_id[entry["ingredient_id"]].update(unit=entry["unit"], unit_price=float(entry["unit_price"]))
            report = {"database": "nutrigenie", "as_of": str(args.as_of), "source_date": bundle["observed_on"], "total_ingredients": len(rows), "reviewed": len(bundle["entries"]), "unreviewed_ids": sorted(set(existing) - {e["ingredient_id"] for e in bundle["entries"]}), "changes": changes, "source_sha256": hashlib.sha256(args.file.read_bytes()).hexdigest(), "status": "preview"}
            if not args.apply:
                db.rollback()
                print(json.dumps(report, ensure_ascii=False, default=str, indent=2))
                return
            seed_after = update_seed_text(seed_before, bundle["entries"])
            if not changes and seed_before == seed_after:
                db.rollback()
                print(json.dumps({"status": "unchanged", "reviewed": len(bundle["entries"])}))
                return
            backup = backend / ".local-backups" / ("market-prices-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
            backup.mkdir(parents=True)
            (backup / "ingredients.json").write_bytes(seed_before)
            shutil.copyfile(args.file, backup / "source.json")
            (backup / "before.json").write_text(json.dumps(rows, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
            report["status"] = "prepared"
            (backup / "report.json").write_text(json.dumps(report, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
            undo = ["-- Conditional rollback: refuses to overwrite a subsequently changed price.", "START TRANSACTION;"]
            for change in changes:
                old, new = change["before"], change["after"]
                cur.execute("UPDATE ingredients SET unit=%s,unit_price=%s WHERE ingredient_id=%s AND name=%s AND unit=%s AND unit_price=%s", (new["unit"], new["unit_price"], old["ingredient_id"], old["name"], old["unit"], old["unit_price"]))
                if cur.rowcount != 1:
                    raise ValueError("数据库发生并发变更")
                undo.append("UPDATE ingredients SET unit={u},unit_price={p} WHERE ingredient_id={i} AND unit={nu} AND unit_price={np};".format(u=db.escape(old["unit"]), p=old["unit_price"], i=old["ingredient_id"], nu=db.escape(new["unit"]), np=new["unit_price"]))
            undo.append("COMMIT;")
            (backup / "restore.sql").write_text("\n".join(undo) + "\n", encoding="utf-8")
            if seed_path.read_bytes() != seed_before:
                raise ValueError("种子文件发生并发变更")
            temp = seed_path.with_suffix(".prices.tmp")
            temp.write_bytes(seed_after)
            temp.replace(seed_path)
            changed_seed = True
            db.commit()
            committed = True
            report["status"] = "committed"
            (backup / "report.json").write_text(json.dumps(report, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
            print(json.dumps({"status": "committed", "updated": len(changes), "reviewed": len(bundle["entries"]), "unreviewed": len(report["unreviewed_ids"]), "backup": str(backup)}, ensure_ascii=False))
    finally:
        if not committed:
            db.rollback()
            if changed_seed:
                seed_path.write_bytes(seed_before)
        db.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except Exception as exc:
        # Avoid printing connection strings, credentials or server error messages.
        print(json.dumps({"status": "failed", "error_class": type(exc).__name__}), file=sys.stderr)
        raise SystemExit(1)
