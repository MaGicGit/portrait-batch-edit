import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from portrait_edit.contact_sheets import make_contact_sheets
from portrait_edit.plan import validate_and_export
from portrait_edit.scanner import scan_lightroom_manifest


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.job = Path(temp.name)
        self.manifest = self.job / "manifest.json"
        self.plan = self.job / "ai-edit-plan.json"
        rows, items = [], []
        for i, group in enumerate(("shade", "sun", "sun")):
            path = self.job / str(i) / "中文,人像.ARW"
            preview = self.job / f"{i}.jpg"
            Image.new("RGB", (20, 40), (35 * i, 10, 45)).save(preview)
            rows.append(dict(source_path=str(path), uuid=f"id-{i}", file_name=path.name, preview_path=preview.name))
            items.append(dict(source_path=str(path), style_group=group, preview_path=str(preview),
                              score=10 + i, preview=(i == 0), global_settings={"Exposure2012": 3},
                              local_adjustments=[{"target": "hair", "status": "proposed_not_applied",
                                                  "instruction": "保留发丝 <test>", "settings": {"Texture": 3}}]))
        manifest_csv = self.job / "lightroom-manifest.csv"
        with manifest_csv.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)
        scan_lightroom_manifest(manifest_csv, self.job)
        self.data = {"schema_version": "1.0", "style_groups": [
            {"id": g, "style_name": g, "rationale": "light"} for g in ("shade", "sun")], "photos": items}

    def export(self):
        self.plan.write_text(json.dumps(self.data), "utf-8")
        return validate_and_export(self.manifest, self.plan, self.job / "output")

    def test_contact_sheets_and_mixed_representatives(self):
        sheets = make_contact_sheets(self.manifest, self.job / "sheets", 2, 1)
        self.assertEqual(len(sheets), 2)
        tiles = json.loads((self.job / "sheets/index.json").read_text("utf-8"))["tiles"]
        self.assertEqual([p["source_path"] for p in tiles], [p["source_path"] for p in self.data["photos"]])
        files = self.export()
        with files["preview_csv"].open(encoding="utf-8-sig", newline="") as f:
            self.assertEqual([r["uuid"] for r in csv.DictReader(f)], ["id-0", "id-2"])
        report = files["report"].read_text("utf-8")
        self.assertIn("保留发丝 &lt;test&gt;", report)
        self.assertIn("3 → 1.0", report)
        first = files["apply_csv"].read_bytes()
        self.assertEqual(first, self.export()["apply_csv"].read_bytes())

    def test_detailed_review_is_ordered_and_separate_from_develop_settings(self):
        def read_rows(path):
            with path.open(encoding="utf-8-sig", newline="") as file:
                return list(csv.DictReader(file))

        app_files = ("preview_csv", "apply_csv")
        item = self.data["photos"][0]
        item["notes"] = "旧版自由备注 <保留>"
        old = self.export()
        old_report = old["report"].read_text("utf-8")
        self.assertIn("旧版自由备注 &lt;保留&gt;", old_report)
        self.assertNotIn("备注与人工复核", old_report)
        for heading in ("位置", "观察依据", "停手条件"):
            self.assertNotIn(f"<dt>{heading}</dt>", old_report)
        original_app_rows = {key: read_rows(old[key]) for key in app_files}

        item["notes"] = "先保留侧光 <亮边>\nPhotoshop 人工复核 <script>\n比较交付尺寸"
        hair = item["local_adjustments"][0]
        hair.update(location='画面左侧,"发梢"', observation="发梢与背景的 <明暗边界>",
                    stop_when="没有白边 & 仍有层次")
        item["local_adjustments"].append(dict(target="background", status="proposed_not_applied",
                                              instruction="保留原有背景层次", settings={}))
        result = self.export()
        report = result["report"].read_text("utf-8")
        expected = ["首要判断", "先保留侧光 &lt;亮边&gt;", "备注与人工复核",
                    "Photoshop 人工复核 &lt;script&gt;\n比较交付尺寸", "全局显影目标值",
                    "画面左侧,&quot;发梢&quot;", "发梢与背景的 &lt;明暗边界&gt;", "保留发丝 &lt;test&gt;",
                    "没有白边 &amp; 仍有层次", "保留原有背景层次"]
        positions = [report.index(part) for part in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("<script>", report)
        rows = read_rows(result["local_adjustments"])
        self.assertEqual(list(rows[0]), ["source_path", "style_group", "target", "status", "instruction",
                                        "settings_json", "location", "observation", "stop_when"])
        self.assertEqual([r["target"] for r in rows], ["hair", "background", "hair", "hair"])
        for key in ("location", "observation", "stop_when"):
            self.assertEqual(rows[0][key], hair[key])
            self.assertEqual(rows[1][key], "")
        self.assertEqual(json.loads(rows[1]["settings_json"]), {})
        normalized = json.loads(result["normalized_plan"].read_text("utf-8"))
        self.assertEqual(normalized["photos"][0]["local_adjustments"], item["local_adjustments"])
        for key in app_files:
            updated = read_rows(result[key])
            original = original_app_rows[key]
            # The review text participates in the revision hash, but supplies no Lightroom settings.
            self.assertNotEqual(updated[0]["revision"], original[0]["revision"])
            for row in updated + original:
                del row["revision"]
            self.assertEqual(original, updated)
            self.assertTrue({"location", "observation", "stop_when", "instruction"}.isdisjoint(updated[0]))

    def test_optional_review_details_must_be_strings(self):
        local = self.data["photos"][0]["local_adjustments"][0]
        for key in ("location", "observation", "stop_when"):
            with self.subTest(field=key):
                local[key] = 5
                with self.assertRaisesRegex(ValueError, key):
                    self.export()
                del local[key]

    def test_invalid_plans_leave_last_good_outputs_intact(self):
        before = self.export()["apply_csv"].read_bytes()
        original = json.dumps(self.data)
        for change in ("missing", "duplicate", "group", "unknown", "bool", "nan", "local", "empty", "score"):
            with self.subTest(change=change):
                self.data = json.loads(original)
                photos = self.data["photos"]
                item = photos[0]
                if change == "missing":
                    photos.pop()
                elif change == "duplicate":
                    photos.append(item)
                elif change == "group":
                    item["style_group"] = "bad"
                elif change == "unknown":
                    item["global_settings"]["MaskGroupBasedCorrections"] = 2
                elif change == "local":
                    item["local_adjustments"][0]["status"] = "applied"
                elif change == "empty":
                    self.data["photos"] = []
                elif change == "score":
                    item["score"] = -10
                else:
                    item["global_settings"]["Exposure2012"] = True if change == "bool" else float("nan")
                with self.assertRaises(ValueError):
                    self.export()
                self.assertEqual((self.job / "output/apply-plan.csv").read_bytes(), before)

    def test_cli_from_external_job_directory(self):
        def run(*args):
            result = subprocess.run([sys.executable, "-X", "utf8", "-m", "portrait_edit.cli", *args],
                                    cwd=self.job, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)

        self.plan.write_text(json.dumps(self.data), "utf-8")
        inputs = {p: p.read_bytes() for p in self.job.glob("*.jpg")}
        run("scan", "--input", ".", "--workdir", "scanned")
        run("scan-lightroom", "--manifest", "lightroom-manifest.csv", "--workdir", ".")
        run("sheets", "--manifest", "manifest.json", "--out", "sheets")
        run("validate", "--manifest", "manifest.json", "--plan", self.plan.name, "--out", "output")
        run("report", "--plan", "output/normalized-plan.json", "--out", "review.html")
        self.assertEqual((self.job / "review.html").read_bytes(), (self.job / "output/report.html").read_bytes())
        self.assertEqual(inputs, {p: p.read_bytes() for p in inputs})
