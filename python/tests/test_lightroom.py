import csv
import hashlib
import io
import json
import tempfile
import unittest
from itertools import count
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from portrait_edit.lightroom_export import export_lightroom
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
        self.g.isAbsolute = lambda p: Path(p).is_absolute()
        self.g.read = lambda p: Path(p).read_bytes().decode("utf-8")
        self.g.exists = lambda p: Path(p).exists()
        def mkdir(p):
            try:
                Path(p).mkdir(parents=True)
            except FileExistsError:
                return True, False
            return True, True

        self.g.mkdir = mkdir
        self.g.move = lambda a, b: bool(Path(a).rename(b))
        self.g.tempDir = str(self.job)
        self.g.requestHome = str(self.job / "测试用户")
        self.g.sourceFolder = str(self.job / "中文, 原片")
        self.g.sourcePath = lambda i: str(Path(self.g.sourceFolder) / str(i) / "同名,人像.ARW")
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

    def request_export(self, **kwargs):
        info = self.lua.execute((PLUGIN / "Info.lua").read_text("utf-8"))
        handler = self.lua.execute((PLUGIN / info.URLHandler).read_text("utf-8")).URLHandler

        def deliver(url):
            self.assertTrue(url.startswith(f"lightroom://{info.LrToolkitIdentifier}/export/"))
            handler(url)
            handler(url)  # A duplicate delivery must not export a second time.
            self.assertIsNone(self.g.lastError)

        with patch.object(Path, "home", return_value=Path(self.g.requestHome)), \
             patch("portrait_edit.lightroom_export._open_lightroom", side_effect=deliver):
            return export_lightroom(**kwargs)

    def test_prompt_exports_selection_without_dialogs_then_catalog_folder(self):
        self.lua.execute('c=import("LrApplication").activeCatalog(); c:setSelectedPhotos(c:findPhotoByUuid("id-2"), {})')
        panels = self.g.panelCount
        self.g.lastMessage = None
        manifest = self.request_export()
        self.assertEqual(manifest.parent.name, "session-001")
        with manifest.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([r["source_path"] for r in rows], [self.g.sourcePath(2)])
        self.assertTrue(Path(rows[0]["preview_path"]).is_file())
        self.assertEqual(self.counts(), [0, 0, 0])
        self.assertEqual(self.g.panelCount, panels)
        self.assertIsNone(self.g.lastMessage)

        self.lua.execute('c:createVirtualCopies("fixture"); c:findPhotoByUuid("id-3").video=true')
        manifest = self.request_export(source_folder=self.g.sourceFolder)
        self.assertEqual(manifest.parent.name, "session-002")
        with manifest.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([r["source_path"] for r in rows], [self.g.sourcePath(1), self.g.sourcePath(2)])
        self.assertEqual(self.counts(), [0, 1, 0])

    def test_prompt_reports_empty_selection_missing_folder_and_cancel(self):
        self.lua.execute('c=import("LrApplication").activeCatalog(); c:setSelectedPhotos(nil, {})')
        out = self.job / "空的 工作目录"
        out.mkdir()
        with self.assertRaisesRegex(RuntimeError, "图库选中原片"):
            self.request_export(workdir=out)
        self.assertEqual(list(out.iterdir()), [])
        self.lua.execute('c:setSelectedPhotos(c:findPhotoByUuid("id-1"), {})')
        with self.assertRaisesRegex(RuntimeError, "未收录"):
            self.request_export(workdir=out, source_folder=self.job / "unknown")
        self.g.cancelProgress = True
        with self.assertRaisesRegex(RuntimeError, "已取消"):
            self.request_export(workdir=out)
        self.assertFalse((out / "lightroom-manifest.csv").exists())
        with self.assertRaisesRegex(FileExistsError, "工作目录已有文件"):
            self.request_export(workdir=out)
        self.assertEqual(self.counts(), [0, 0, 0])

    def test_unclaimed_request_expires_and_stalled_export_is_not_accepted(self):
        job = self.job / "pending-job"
        with patch.object(Path, "home", return_value=Path(self.g.requestHome)), \
             patch("portrait_edit.lightroom_export.time.sleep"), \
             patch("portrait_edit.lightroom_export.time.monotonic", side_effect=count(0, 15)), \
             patch("portrait_edit.lightroom_export._open_lightroom") as dispatch:
            with self.assertRaisesRegex(TimeoutError, "未接收"):
                export_lightroom(workdir=job)
            self.assertGreater(dispatch.call_count, 1)
            self.assertEqual(len({call.args[0] for call in dispatch.call_args_list}), 1)
            info = self.lua.execute((PLUGIN / "Info.lua").read_text("utf-8"))
            handler = self.lua.execute((PLUGIN / info.URLHandler).read_text("utf-8")).URLHandler
            handler(dispatch.call_args.args[0])  # A late URL cannot resurrect an expired request.
            self.assertEqual(list(job.iterdir()), [])

            def stall(url):
                request = Path(self.g.requestHome) / "PortraitBatchEdit/requests" / url.rsplit("/", 1)[1]
                (request / "pending.csv").rename(request / "running.csv")
                (job / "lightroom-manifest.tmp").write_text("partial", encoding="utf-8")

            dispatch.side_effect = stall
            with self.assertRaisesRegex(TimeoutError, "已接收请求"):
                export_lightroom(workdir=job)
            self.assertTrue((job / "lightroom-manifest.tmp").is_file())
            self.assertFalse((job / "lightroom-manifest.csv").exists())

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
