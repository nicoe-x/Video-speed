# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
"""Local FFmpeg batch conversion. No network or source-file mutations."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid

EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.wmv', '.flv', '.webm', '.m4v', '.mts', '.m2ts', '.ts', '.mpeg', '.mpg', '.3gp', '.vob'}
HIDDEN = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


class Cancelled(Exception):
    pass


def binary(name: str) -> str:
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    for path in (root / 'tools' / f'{name}.exe', root / f'{name}.exe'):
        if path.is_file():
            return str(path)
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError(f'缺少 {name}，请使用包含 tools 文件夹的完整软件包。')


def validate_speed(value) -> float:
    speed = float(value)
    if not math.isfinite(speed) or not 0.25 <= speed <= 16:
        raise ValueError('倍速请输入 0.25 到 16 之间的数字。')
    return speed


def tempo_filter(speed: float) -> str:
    speed = validate_speed(speed)
    factors = []
    while speed > 2:
        factors.append(2)
        speed /= 2
    while speed < 0.5:
        factors.append(0.5)
        speed /= 0.5
    factors.append(speed)
    return 'asetpts=PTS-STARTPTS,' + ','.join(f'atempo={x:.12g}' for x in factors)


def collect_folder(folder: Path, recursive: bool, excluded: Path | None = None, cancel=None):
    """Do not follow directory links or re-import our default output directory."""
    result = []
    folder = folder.resolve()
    for current, dirs, files in os.walk(folder, followlinks=False):
        if cancel and cancel.is_set():
            raise Cancelled()
        dirs[:] = sorted(d for d in dirs if d != '倍速输出' and not (Path(current) / d).is_symlink()
                         and (excluded is None or (Path(current) / d).resolve() != excluded.resolve()))
        result.extend(Path(current) / f for f in sorted(files) if Path(f).suffix.lower() in EXTENSIONS)
        if not recursive:
            break
    return result


class Converter:
    def __init__(self):
        self.cancelled = threading.Event()
        self._lock = threading.Lock()
        self._process = None

    def cancel(self):
        self.cancelled.set()
        with self._lock:
            if self._process and self._process.poll() is None:
                try:
                    self._process.terminate()
                except OSError:
                    pass

    def _start(self, args, **kwargs):
        with self._lock:
            if self.cancelled.is_set():
                raise Cancelled()
            self._process = subprocess.Popen(args, **HIDDEN, **kwargs)
            return self._process

    def probe(self, source: Path):
        proc = self._start([binary('ffprobe'), '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(source)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise RuntimeError('读取视频信息超时。')
        if self.cancelled.is_set():
            raise Cancelled()
        if proc.returncode:
            raise RuntimeError('无法读取视频：' + stderr.decode('utf-8', errors='replace')[-1200:])
        data = json.loads(stdout)
        videos = [s for s in data['streams'] if s['codec_type'] == 'video' and not s.get('disposition', {}).get('attached_pic')]
        if not videos:
            raise RuntimeError('文件中没有可处理的视频画面。')
        video = videos[0]
        duration = float(video.get('duration') or data.get('format', {}).get('duration') or 0)
        if not math.isfinite(duration) or duration <= 0:
            raise RuntimeError('无法确定视频时长。')
        try:
            n, d = video.get('avg_frame_rate', '30/1').split('/')
            fps = float(n) / float(d)
            if not math.isfinite(fps) or fps <= 0:
                fps = 30
        except (ValueError, ZeroDivisionError):
            fps = 30
        return duration, min(fps, 60), video['index']

    def convert(self, source: Path, output_dir: Path, speed: float, mute=False, quality='标准', progress=lambda x: None):
        source = source.resolve(strict=True)
        speed = validate_speed(speed)
        duration, fps, stream_index = self.probe(source)
        output_dir.mkdir(parents=True, exist_ok=True)
        temporary = output_dir / f'.speed-{uuid.uuid4().hex}.mp4'
        target = None
        args = [binary('ffmpeg'), '-hide_banner', '-nostdin', '-y', '-loglevel', 'error', '-i', str(source),
                '-map', f'0:{stream_index}', '-vf', f'setpts=(PTS-STARTPTS)/{speed:.12g},fps={fps:.10g},scale=ceil(iw/2)*2:ceil(ih/2)*2',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', {'高画质': '18', '标准': '21', '小体积': '26'}[quality],
                '-pix_fmt', 'yuv420p']
        if mute:
            args += ['-an']
        else:
            args += ['-map', '0:a?', '-af', tempo_filter(speed), '-c:a', 'aac', '-b:a', '192k']
        args += ['-sn', '-dn', '-map_metadata', '-1', '-movflags', '+faststart', '-progress', 'pipe:1', '-nostats', str(temporary)]
        try:
            with tempfile.TemporaryFile() as errors:
                proc = self._start(args, stdout=subprocess.PIPE, stderr=errors, text=True, encoding='utf-8', errors='replace')
                try:
                    for line in proc.stdout:
                        if line.startswith('out_time_us='):
                            try:
                                progress(min(0.99, max(0, int(line.split('=', 1)[1]) / 1_000_000 / (duration / speed))))
                            except ValueError:
                                pass
                    proc.wait()
                finally:
                    proc.stdout.close()
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait()
                if self.cancelled.is_set():
                    raise Cancelled()
                if proc.returncode or not temporary.exists() or temporary.stat().st_size == 0:
                    errors.seek(0, 2)
                    end = errors.tell()
                    errors.seek(max(0, end - 2400))
                    raise RuntimeError(errors.read().decode('utf-8', errors='replace') or '编码失败。')
            # Reserve with exclusive creation: never overwrite a source or existing export.
            stem = f'{source.stem}_{speed:g}x'
            index = 0
            while True:
                candidate = output_dir / f'{stem}{"" if index == 0 else f"_{index}"}.mp4'
                try:
                    with candidate.open('xb'):
                        pass
                    target = candidate
                    break
                except FileExistsError:
                    index += 1
            try:
                temporary.replace(target)
            except BaseException:
                target.unlink(missing_ok=True)
                raise
            progress(1)
            return target
        finally:
            temporary.unlink(missing_ok=True)
