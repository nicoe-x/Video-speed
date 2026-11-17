# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
import os
import io
from pathlib import Path
import shutil
import threading
import uuid

from PIL import Image, ImageOps
from core import Cancelled

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}


def validate_image_options(quality, max_edge, output_format, target_kb=0, allow_resize=False):
    try:
        quality, max_edge, target_kb = int(quality), int(max_edge), int(target_kb)
    except (TypeError, ValueError):
        raise ValueError('画质、最长边和文件体积请输入整数。') from None
    if not 10 <= quality <= 95:
        raise ValueError('图片画质请输入 10～95 的整数。')
    if not 0 <= max_edge <= 20000:
        raise ValueError('最长边请输入 0～20000 的整数，0 表示不缩放。')
    if not 0 <= target_kb <= 102400:
        raise ValueError('文件体积请输入 0～102400 KB，0 表示不限制。')
    if output_format not in ('自动（JPG/WebP）', '原格式', 'JPEG', 'PNG', 'WebP'):
        raise ValueError('不支持的输出格式。')
    return dict(quality=quality, max_edge=max_edge, output_format=output_format,
                target_kb=target_kb, allow_resize=bool(allow_resize))


class ImageCompressor:
    def __init__(self):
        self.cancelled = threading.Event()

    def cancel(self):
        self.cancelled.set()

    def check_cancel(self):
        if self.cancelled.is_set():
            raise Cancelled()

    def compress(self, source, output_dir, quality=80, max_edge=0, output_format='原格式', progress=lambda x: None,
                 target_kb=0, allow_resize=False):
        validate_image_options(quality, max_edge, output_format, target_kb, allow_resize)
        source, output_dir = Path(source).resolve(strict=True), Path(output_dir)
        self.check_cancel()
        output_dir.mkdir(parents=True, exist_ok=True)
        temporary = output_dir / f'.image-{uuid.uuid4().hex}.tmp'
        try:
            with Image.open(source) as original:
                if getattr(original, 'n_frames', 1) > 1:
                    raise ValueError('不处理动图或多页图片，请先导出为单张图片。')
                if output_format == '自动（JPG/WebP）':
                    fmt = 'WEBP' if ('A' in original.getbands() or 'transparency' in original.info) else 'JPEG'
                else:
                    fmt = {'原格式': original.format, 'WebP': 'WEBP'}.get(output_format, output_format)
                if fmt not in ('JPEG', 'PNG', 'WEBP'):
                    fmt = 'PNG'
                image = ImageOps.exif_transpose(original)
                original_size = image.size
                image.load()
                self.check_cancel()
                progress(.25)
                if max_edge:
                    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
                icc = image.info.get('icc_profile')
                for metadata in ('exif', 'xmp', 'comment', 'XML:com.adobe.xmp'):
                    image.info.pop(metadata, None)
                if fmt == 'JPEG':
                    if image.mode not in ('RGB', 'L'):
                        rgba = image.convert('RGBA')
                        image = Image.new('RGB', rgba.size, 'white')
                        image.paste(rgba, mask=rgba.getchannel('A'))
                        icc = None
                    options = dict(quality=quality, optimize=True, progressive=True)
                elif fmt == 'PNG':
                    if image.mode not in ('1', 'L', 'LA', 'P', 'RGB', 'RGBA', 'I', 'I;16'):
                        image = image.convert('RGB')
                        icc = None
                    options = dict(optimize=True, compress_level=9)
                else:
                    if image.mode not in ('RGB', 'RGBA'):
                        image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
                    options = dict(quality=quality, method=6)
                if icc:
                    options['icc_profile'] = icc
                if (target_kb and output_format == '自动（JPG/WebP）' and not max_edge
                        and original.format in ('JPEG', 'PNG', 'WEBP')
                        and source.stat().st_size <= target_kb * 1024):
                    shutil.copyfile(source, temporary)
                    fmt = original.format
                elif target_kb:
                    limit = target_kb * 1024
                    while True:
                        self.check_cancel()
                        best = None
                        if fmt == 'PNG':
                            buffer = io.BytesIO()
                            image.save(buffer, format=fmt, **options)
                            if buffer.tell() <= limit:
                                best = buffer.getvalue()
                        else:
                            low, high = 10, quality
                            while low <= high:
                                self.check_cancel()
                                q = (low + high) // 2
                                buffer = io.BytesIO()
                                image.save(buffer, format=fmt, **dict(options, quality=q))
                                if buffer.tell() <= limit:
                                    best = buffer.getvalue()
                                    low = q + 1
                                else:
                                    high = q - 1
                        if best is not None:
                            temporary.write_bytes(best)
                            break
                        if not allow_resize or image.size == (1, 1):
                            raise ValueError(f'无法压到 {target_kb} KB 以内。可选择自动格式、增大体积上限，或允许缩小尺寸。')
                        image = image.resize((max(1, int(image.width * .8)), max(1, int(image.height * .8))),
                                             Image.Resampling.LANCZOS)
                else:
                    image.save(temporary, format=fmt, **options)
                self.check_cancel()
                progress(.9)
                # An already optimized original should not become a larger export.
                if (output_format == '原格式' and fmt == original.format and image.size == original_size
                        and temporary.stat().st_size >= source.stat().st_size):
                    if not target_kb or source.stat().st_size <= target_kb * 1024:
                        shutil.copyfile(source, temporary)
            self.check_cancel()
            suffix = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}[fmt]
            index = 0
            while True:
                target = output_dir / f'{source.stem}_压缩{("_" + str(index)) if index else ""}{suffix}'
                try:
                    with target.open('xb'):
                        pass
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
