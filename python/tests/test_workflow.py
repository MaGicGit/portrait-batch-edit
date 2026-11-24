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
