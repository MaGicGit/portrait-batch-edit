"""Request previews from the local Lightroom Classic plug-in and wait for publication."""

from __future__ import annotations

import csv
import os
import tempfile
import time
from itertools import count
from pathlib import Path


def _new_workdir(workdir: str | Path | None, base: Path) -> Path:
    if workdir is not None:
        job = Path(workdir).expanduser().resolve()
        job.mkdir(parents=True, exist_ok=True)
        if any(job.iterdir()):
            raise FileExistsError(f"工作目录已有文件，请指定新的工作目录：{job}")
        return job
    for number in count(1):
        job = base / "jobs" / f"session-{number:03d}"
        try:
            job.mkdir(parents=True)
        except FileExistsError:
            continue
        return job


def _open_lightroom(url: str) -> None:
    if not hasattr(os, "startfile"):
        raise OSError("自动请求预览需要 Windows 和 Lightroom Classic")
    try:
        os.startfile(url)
    except OSError as exc:
        raise OSError("Windows 无法打开 Lightroom 链接，请检查 Lightroom Classic 的安装") from exc


def _wait_for_export(request: Path, job: Path) -> Path:
    url = f"lightroom://com.example.portraitbatchedit/export/{request.name}"
    pending = request / "pending.csv"
    start = time.monotonic()
    next_delivery = start
    while pending.is_file():
        now = time.monotonic()
        if now - start >= 90:
            raise TimeoutError("Lightroom 未接收导出请求。请打开相应目录，在增效工具管理器中启用或重新载入 Portrait Batch Edit 后重试。")
        if now >= next_delivery:
            # Classic may finish starting up after the first URL was delivered.
            _open_lightroom(url)
            next_delivery = now + 20
        else:
            time.sleep(0.5)

    manifest = job / "lightroom-manifest.csv"
    previews = job / "previews"
    last_change, previous_stamp = time.monotonic(), None
    while True:
        if (request / "failed").is_file():
            detail = request / "error.txt"
            message = detail.read_text(encoding="utf-8") if detail.is_file() else "请查看 Lightroom 的错误提示"
            raise RuntimeError(f"预览导出失败：{message}")
        if (request / "done").is_file():
            if manifest.is_file():
                return manifest
            raise RuntimeError(f"Lightroom 已返回，但未找到导出清单：{manifest}")
        # The exporter creates a new JPEG for each photo. Allow long batches while
        # detecting a host that quit or stopped responding during a thumbnail request.
        stamp = previews.stat().st_mtime_ns if previews.is_dir() else None
        if stamp != previous_stamp:
            last_change, previous_stamp = time.monotonic(), stamp
        if time.monotonic() - last_change >= 180:
            raise TimeoutError(f"Lightroom 已接收请求，三分钟内未见导出进度。请检查 Lightroom。工作目录：{job}")
        time.sleep(0.5)


def export_lightroom(workdir: str | Path | None = None, source_folder: str | Path | None = None) -> Path:
    base = Path.home() / "PortraitBatchEdit"
    folder = ""
    if source_folder is not None:
        if not str(source_folder).strip():
            raise ValueError("请指定原片目录的路径")
        folder = str(Path(source_folder).expanduser().absolute())
    job = _new_workdir(workdir, base)
    inbox = base / "requests"
    inbox.mkdir(parents=True, exist_ok=True)
    # Only control files live here. All JPEGs and the manifest belong to the job.
    with tempfile.TemporaryDirectory(dir=inbox, prefix="req-") as temp:
        request = Path(temp)
        with (request / "pending.csv").open("x", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(("workdir", "source_folder"))
            writer.writerow((str(job), folder))
        return _wait_for_export(request, job)
