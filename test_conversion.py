# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
"""Integration tests use generated media only; never user videos."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest

from core import Cancelled, Converter, HIDDEN, binary, collect_folder, tempo_filter, validate_speed


def inspect(path):
    return json.loads(subprocess.check_output([binary('ffprobe'), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], **HIDDEN))


class ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='倍速测试_')
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / '中文 视频.mp4'
        subprocess.run([binary('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=30',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '8',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', str(cls.source)], check=True, **HIDDEN)
        cls.original_hash = hashlib.sha256(cls.source.read_bytes()).hexdigest()

    @classmethod
    def tearDownClass(cls):
        assert hashlib.sha256(cls.source.read_bytes()).hexdigest() == cls.original_hash
        cls.temp.cleanup()

    def test_speed_and_audio_sync(self):
        for speed in (0.25, 0.5, 1.5, 2, 4, 16):
            with self.subTest(speed=speed):
                updates = []
                result = Converter().convert(self.source, self.root / 'exports', speed, progress=updates.append)
                data = inspect(result)
                video = next(s for s in data['streams'] if s['codec_type'] == 'video')
                audio = next(s for s in data['streams'] if s['codec_type'] == 'audio')
                self.assertAlmostEqual(float(video['duration']), 8 / speed, delta=0.08)
                self.assertAlmostEqual(float(audio['duration']), float(video['duration']), delta=0.16)
                self.assertEqual(video['codec_name'], 'h264')
                self.assertEqual(updates[-1], 1)
                self.assertTrue(all(0 <= v <= 1 for v in updates))

    def test_collision_and_mute(self):
        out = self.root / 'collision'
        first = Converter().convert(self.source, out, 2, mute=True)
        digest = hashlib.sha256(first.read_bytes()).digest()
        second = Converter().convert(self.source, out, 2, mute=True)
        self.assertNotEqual(first, second)
        self.assertEqual(hashlib.sha256(first.read_bytes()).digest(), digest)
        self.assertFalse(any(s['codec_type'] == 'audio' for s in inspect(second)['streams']))

    def test_silent_input(self):
        source = self.root / 'silent.mkv'
        subprocess.run([binary('ffmpeg'), '-v', 'error', '-i', str(self.source), '-an', '-c:v', 'copy', str(source)], check=True, **HIDDEN)
        output = Converter().convert(source, self.root / 'silent-out', 2)
        self.assertEqual(len(inspect(output)['streams']), 1)

    def test_cancel_removes_partial(self):
        converter = Converter()
        folder = self.root / 'cancel'
        def cancel_on_progress(_):
            converter.cancel()
        with self.assertRaises(Cancelled):
            converter.convert(self.source, folder, 0.25, progress=cancel_on_progress)
        self.assertEqual(list(folder.iterdir()), [])

    def test_cancel_before_probe(self):
        converter = Converter()
        converter.cancel()
        with self.assertRaises(Cancelled):
            converter.convert(self.source, self.root / 'cancel-before', 2)

    def test_invalid_file_and_speed(self):
        bad = self.root / '损坏.mp4'
        bad.write_text('not a video')
        with self.assertRaises(RuntimeError):
            Converter().convert(bad, self.root / 'bad-out', 2)
        for speed in ('nan', 'inf', '0', '-1', '17'):
            with self.assertRaises(ValueError):
                validate_speed(speed)

    def test_scan_excludes_exports(self):
        folder = self.root / 'scan'
        (folder / 'child').mkdir(parents=True)
        (folder / '倍速输出').mkdir()
        for file in (folder / 'a.mp4', folder / 'child' / 'b.MOV', folder / '倍速输出' / 'c.mp4'):
            file.touch()
        self.assertEqual(len(collect_folder(folder, False)), 1)
        self.assertEqual(len(collect_folder(folder, True)), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
