# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from core import Cancelled, collect_folder
from cover_core import COVER_LIMIT, COVER_PRESETS, CoverMaker, frame_cover, validate_cover_options
from image_core import IMAGE_EXTENSIONS


class CoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / '封面输出'
        self.source = self.root / '封面.png'
        Image.effect_noise((1000, 600), 60).convert('RGB').save(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def test_both_presets_compliance_and_original_unchanged(self):
        before = self.source.read_bytes()
        results = CoverMaker().make(self.source, self.out)
        self.assertEqual(len(results), 2)
        for result, (name, minimum) in zip(results, COVER_PRESETS.items()):
            self.assertIn(name, result.name)
            self.assertLessEqual(result.stat().st_size, COVER_LIMIT)
            with Image.open(result) as image:
                self.assertEqual(image.format, 'JPEG')
                self.assertEqual(image.size, tuple(x * 2 for x in minimum))
                self.assertEqual(image.width * minimum[1], image.height * minimum[0])
        self.assertEqual(before, self.source.read_bytes())

    def test_small_images_minimum_and_collision(self):
        Image.new('RGB', (10, 8), 'blue').save(self.source)
        maker = CoverMaker()
        first = maker.make(self.source, self.out, platform='抖音', size='最低尺寸')[0]
        content = first.read_bytes()
        second = maker.make(self.source, self.out, platform='抖音', size='最低尺寸')[0]
        self.assertNotEqual(first, second)
        self.assertEqual(first.read_bytes(), content)
        with Image.open(second) as image:
            self.assertEqual(image.size, (480, 720))

    def test_crop_and_padding_keep_correct_content(self):
        image = Image.new('RGB', (300, 100), 'red')
        image.paste('blue', (100, 0, 200, 100))
        crop = frame_cover(image, (70, 100), '居中裁剪')
        self.assertEqual(crop.getpixel((5, 50)), (0, 0, 255))
        pad = frame_cover(image, (70, 100), '留白保留全图')
        self.assertEqual(pad.getpixel((35, 0)), (255, 255, 255))
        self.assertEqual(pad.getpixel((5, 50)), (255, 0, 0))
        self.assertEqual(pad.getpixel((35, 50)), (0, 0, 255))

    def test_transparency_and_exif_orientation(self):
        Image.new('RGBA', (70, 100), (255, 0, 0, 0)).save(self.source)
        result = CoverMaker().make(self.source, self.out, platform='红果')[0]
        with Image.open(result) as image:
            self.assertEqual(image.getpixel((350, 500)), (255, 255, 255))
        source = self.root / '旋转.jpg'
        exif = Image.Exif()
        exif[274] = 6
        Image.new('RGB', (100, 70), 'red').save(source, exif=exif)
        result = CoverMaker().make(source, self.out, platform='红果', size='最低尺寸')[0]
        with Image.open(result) as image:
            self.assertGreater(image.getpixel((175, 1))[0], 240)
            self.assertLess(image.getpixel((175, 1))[1], 20)
            self.assertNotIn(274, image.getexif())

    def test_size_limit_reduces_quality_and_failure_leaves_no_files(self):
        with patch('cover_core.COVER_LIMIT', 40_000):
            result = CoverMaker().make(self.source, self.out, platform='红果')[0]
            self.assertLessEqual(result.stat().st_size, 40_000)
        before = set(self.out.iterdir())
        with patch('cover_core.COVER_LIMIT', 10), self.assertRaises(ValueError):
            CoverMaker().make(self.source, self.out)
        self.assertEqual(set(self.out.iterdir()), before)

    def test_cancellation_discards_all_pending_versions(self):
        maker = CoverMaker()
        with self.assertRaises(Cancelled):
            maker.make(self.source, self.out, progress=lambda _: maker.cancel())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_invalid_inputs_and_options(self):
        for options in [('其他', '留白保留全图', '标准尺寸'), ('红果', '拉伸', '标准尺寸'),
                        ('抖音', '居中裁剪', '其他')]:
            with self.assertRaises(ValueError):
                validate_cover_options(*options)
        self.source.write_bytes(b'broken')
        with self.assertRaises(OSError):
            CoverMaker().make(self.source, self.out)
        frames = [Image.new('RGB', (20, 20), color) for color in ('red', 'blue')]
        animation = self.root / '动画.png'
        frames[0].save(animation, save_all=True, append_images=frames[1:])
        with self.assertRaises(ValueError):
            CoverMaker().make(animation, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_folder_scan_skips_cover_exports(self):
        CoverMaker().make(self.source, self.out)
        self.assertEqual(collect_folder(self.root, True, extensions=IMAGE_EXTENSIONS), [self.source])


if __name__ == '__main__':
    unittest.main()
