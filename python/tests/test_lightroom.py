import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from portrait_edit.plan import BOUNDS, validate_and_export
from portrait_edit.scanner import scan_lightroom_manifest

try:
    from lupa.lua51 import LuaRuntime
except ImportError:
    LuaRuntime = None

PLUGIN = Path(__file__).resolve().parents[2] / "lightroom-plugin/PortraitBatchEdit.lrplugin"


@unittest.skipUnless(LuaRuntime, "Install the test extra for Lua 5.1 SDK simulation")
class LightroomWorkflow(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.job = Path(temp.name)
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.g = self.lua.globals()
        self.g.package.path = str(PLUGIN / "?.lua")
        self.g.md5 = lambda s: hashlib.md5(s.encode()).hexdigest()
        self.g.leaf = lambda p: Path(p).name
        self.g.parent = lambda p: str(Path(p).parent)
        self.g.child = lambda a, b: str(Path(a) / b)
        self.g.read = lambda p: Path(p).read_bytes().decode("utf-8")
        self.g.exists = lambda p: Path(p).exists()
        self.g.mkdir = lambda p: Path(p).mkdir(parents=True, exist_ok=True)
        self.g.move = lambda a, b: bool(Path(a).rename(b))
        self.g.sourcePath = lambda i: str(self.job / str(i) / "同名,人像.ARW")
        jpg = io.BytesIO()
        Image.new("RGB", (20, 40)).save(jpg, format="JPEG")
        self.g.jpegBytes = jpg.getvalue()
        self.lua.execute(Path(__file__).with_name("catalog_fixture.lua").read_text("utf-8"))
        self.g.chosenPath = str(self.job)
        self.execute("ExportPreviews")
        self.assertIsNone(self.g.lastError)
        path = scan_lightroom_manifest(self.job / "lightroom-manifest.csv", self.job)
        self.manifest = json.loads(path.read_text("utf-8"))
        self.plan = {"schema_version": "1.0", "style_groups": [
            {"id": g, "style_name": g, "rationale": "测试"} for g in ("A","B")], "photos": []}
        for i, source in enumerate(self.manifest["photos"]):
            self.plan["photos"].append({**{k: source[k] for k in ("source_path","preview_path")},
                                        "style_group": "A" if i < 2 else "B",
                                        "global_settings": {"Exposure2012": i / 3}})
        self.compile_plan()

    def compile_plan(self):
        plan = self.job / "ai-edit-plan.json"
        plan.write_text(json.dumps(self.plan), encoding="utf-8")
        validate_and_export(self.job / "manifest.json", plan, self.job / "output")

    def execute(self, script):
        self.g.lastError = None
        self.lua.execute((PLUGIN / (script + ".lua")).read_text("utf-8"))

    def apply(self, mode):
        self.g.chosenPath = str(self.job / "output" / (mode + "-plan.csv"))
        self.execute("ApplyPlan")
        return self.g.lastError or ""

    def counts(self):
        return [self.g.copyCount(i) for i in range(1, 4)]

    def test_preview_approval_retries_and_masters(self):
        self.assertIn("代表照", self.apply("apply"))
        self.assertEqual(self.counts(), [0, 0, 0])
        self.g.answer = "cancel"
        self.assertFalse(self.apply("preview"))
        self.assertEqual(self.counts(), [0, 0, 0])
        self.g.answer = "ok"
        self.g.failApply = True
        self.assertIn("simulated write failure", self.apply("preview"))
        self.assertEqual(self.counts(), [1, 0, 0])
        self.assertFalse(self.apply("preview"))
        self.assertEqual(self.counts(), [1, 0, 1])
        self.g.answer = "cancel"
        self.assertFalse(self.apply("apply"))
        self.assertEqual(self.counts(), [1, 0, 1])
        self.g.answer = "ok"
        self.assertFalse(self.apply("apply"))
        self.assertFalse(self.apply("apply"))
        self.assertEqual(self.counts(), [1, 1, 1])
        for i in range(1, 4):
            self.assertEqual(self.g.settings(i, False).Exposure2012, 0.2)
            self.assertAlmostEqual(self.g.settings(i, True).Exposure2012, (i - 1) / 3)
            self.assertEqual(self.g.settings(i, True).Texture, 3)
        self.plan["photos"][1]["global_settings"]["Exposure2012"] = 0.8
        self.compile_plan()
        self.assertIn("代表照", self.apply("apply"))
        self.assertEqual(self.counts(), [1, 1, 1])

    def test_stale_source_and_manually_changed_preview(self):
        self.assertFalse(self.apply("preview"))
        self.g.settings(2, False).Exposure2012 = 0.5
        self.assertIn("原片显影设置已更改", self.apply("apply"))
        self.g.settings(2, False).Exposure2012 = 0.2
        self.g.settings(1, True).Texture = 7
        self.assertIn("手动修改", self.apply("apply"))
        self.assertEqual(self.counts(), [1, 0, 1])

    def test_bounds_and_mismatched_csv(self):
        bounds = self.lua.eval('require("Bounds")')
        self.assertEqual({k: [v[1], v[2]] for k, v in bounds.items()},
                         {k: [v["min"], v["max"]] for k,v in BOUNDS.items()})
        path = self.job / "output/preview-plan.csv"
        path.write_bytes(path.read_bytes().replace(b"id-1", b"id-2"))
        self.assertIn("不一致", self.apply("preview"))
        self.assertEqual(self.counts(), [0, 0, 0])

    def test_unapplied_settings_are_not_marked_complete(self):
        self.g.ignoreApply = True
        self.assertIn("未保留目标参数", self.apply("preview"))
        self.assertIn("代表照", self.apply("apply"))
        self.g.ignoreApply = False
        self.assertFalse(self.apply("preview"))
        self.assertEqual(self.counts(), [1, 0, 1])

    def test_export_cancel_does_not_publish_a_partial_manifest(self):
        other = self.job / "another-job"
        other.mkdir()
        self.g.chosenPath = str(other)
        self.g.cancelProgress = True
        self.execute("ExportPreviews")
        self.assertIsNone(self.g.lastError)
        self.assertFalse((other / "lightroom-manifest.csv").exists())
