# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from image_core import ImageCompressor, IMAGE_EXTENSIONS, validate_image_options
from core import Cancelled, collect_folder


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.out = self.root / '图片压缩输出'

    def tearDown(self):
        self.temp.cleanup()

    def test_jpeg_compression_resize_collision(self):
        source = self.root / '照片.jpg'
        Image.effect_noise((1000, 600), 80).convert('RGB').save(source, quality=98)
        before = source.read_bytes()
        engine = ImageCompressor()
        a = engine.compress(source, self.out, quality=65, max_edge=500)
        b = engine.compress(source, self.out, quality=65, max_edge=500)
        self.assertNotEqual(a, b)
        self.assertLess(a.stat().st_size, source.stat().st_size)
        self.assertEqual(before, source.read_bytes())
        with Image.open(a) as image:
            self.assertEqual(image.size, (500, 300))

    def test_png_transparency_lossless(self):
        source = self.root / '透明.png'
        image = Image.new('RGBA', (100, 70), (30, 80, 120, 45))
        image.save(source, compress_level=0)
        result = ImageCompressor().compress(source, self.out)
        with Image.open(result) as output:
            self.assertEqual(output.tobytes(), image.tobytes())
        self.assertLess(result.stat().st_size, source.stat().st_size)

    def test_webp_and_white_background(self):
        source = self.root / '透明.png'
        Image.new('RGBA', (100, 70), (0, 0, 0, 0)).save(source)
        for fmt in ('JPEG', 'WebP'):
            result = ImageCompressor().compress(source, self.out, output_format=fmt)
            with Image.open(result) as image:
                if fmt == 'JPEG':
                    self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
                else:
                    self.assertEqual(image.getpixel((0, 0))[3], 0)

    def test_orientation(self):
        source = self.root / '旋转.jpg'
        exif = Image.Exif()
        exif[274] = 6
        Image.new('RGB', (80, 40), 'red').save(source, exif=exif)
        output = ImageCompressor().compress(source, self.out, output_format='PNG')
        with Image.open(output) as image:
            self.assertEqual(image.size, (40, 80))
            self.assertIn(image.getexif().get(274), (None, 1))

    def test_animation_and_corruption(self):
        source = self.root / '动画.webp'
        Image.new('RGB', (20, 20), 'red').save(source, save_all=True,
            append_images=[Image.new('RGB', (20, 20), 'blue')], duration=100)
        with self.assertRaisesRegex(ValueError, '不处理动图'):
            ImageCompressor().compress(source, self.out)
        source.write_bytes(b'broken')
        with self.assertRaises(OSError):
            ImageCompressor().compress(source, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_cancel_cleanup(self):
        source = self.root / '图.png'
        Image.new('RGB', (20, 20), 'red').save(source)
        engine = ImageCompressor()
        with self.assertRaises(Cancelled):
            engine.compress(source, self.out, progress=lambda _: engine.cancel())
        self.assertEqual(list(self.out.iterdir()), [])

    def test_optimized_original_not_larger(self):
        source = self.root / '原图.webp'
        Image.new('RGB', (20, 20), 'red').save(source, quality=10)
        result = ImageCompressor().compress(source, self.out, quality=95)
        self.assertLessEqual(result.stat().st_size, source.stat().st_size)

    def test_scan_and_validation(self):
        self.out.mkdir()
        (self.root / 'a.JPG').touch()
        (self.out / 'b.png').touch()
        self.assertEqual(collect_folder(self.root, True, extensions=IMAGE_EXTENSIONS), [self.root / 'a.JPG'])
        for args in ((0, 0, 'PNG'), (80, -1, 'PNG'), (80, 0, 'bad')):
            with self.assertRaises(ValueError):
                validate_image_options(*args)


if __name__ == '__main__':
    unittest.main()
