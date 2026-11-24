import json
import tempfile
import unittest
from pathlib import Path

from portrait_edit.plan import validate_and_export


class PlanTests(unittest.TestCase):
    def test_exports_csv_and_clamps_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "photo.ARW"
            preview = root / "photo.jpg"
            source.write_bytes(b"raw-placeholder")
            preview.write_bytes(b"jpeg-placeholder")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "photos": [{
                    "source_path": str(source),
                    "preview_path": str(preview),
                    "file_name": source.name
                }]
            }), encoding="utf-8")
            plan = root / "plan.json"
            plan.write_text(json.dumps({
                "schema_version": "1.0",
                "style_groups": [{"id": "g1", "style_name": "Open shade", "rationale": "test"}],
                "photos": [{
                    "source_path": str(source),
                    "preview_path": str(preview),
                    "style_group": "g1",
                    "score": 90,
                    "preview": True,
                    "global_settings": {"Exposure2012": 5, "Highlights2012": -25},
                    "local_adjustments": [{"target": "facial_skin", "status": "proposed_not_applied", "instruction": "test"}]
                }]
            }), encoding="utf-8")
            out = root / "out"
            paths = validate_and_export(manifest, plan, out)
            csv_text = paths["apply_csv"].read_text(encoding="utf-8-sig")
            self.assertIn("Exposure2012", csv_text)
            self.assertIn(",1.0,", csv_text)
            self.assertTrue(paths["preview_csv"].exists())
            self.assertTrue(paths["local_adjustments"].exists())


if __name__ == "__main__":
    unittest.main()
