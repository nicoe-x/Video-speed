# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
import io
from pathlib import Path
import uuid

from PIL import Image, ImageOps

from image_core import ImageCompressor


# Requirements supplied in the upload form: ratio, minimum pixels, <= 5 MB.
COVER_PRESETS = {'红果': (350, 500), '抖音': (480, 720)}
COVER_LIMIT = 5_000_000


def validate_cover_options(platform, framing, size):
    if platform not in (*COVER_PRESETS, '同时导出两种'):
        raise ValueError('请选择红果、抖音或同时导出两种。')
    if framing not in ('留白保留全图', '居中裁剪'):
        raise ValueError('请选择留白或居中裁剪。')
    if size not in ('标准尺寸', '最低尺寸'):
        raise ValueError('请选择标准尺寸或最低尺寸。')
    return dict(platform=platform, framing=framing, size=size)


def cover_dimensions(platform, size):
    width, height = COVER_PRESETS[platform]
    factor = 2 if size == '标准尺寸' else 1
    return width * factor, height * factor


def frame_cover(image, dimensions, framing):
    # Flatten transparency onto white before fitting/cropping, including palette PNG.
    rgba = image.convert('RGBA')
    opaque = Image.new('RGB', rgba.size, 'white')
    opaque.paste(rgba, mask=rgba.getchannel('A'))
    if framing == '居中裁剪':
        return ImageOps.fit(opaque, dimensions, method=Image.Resampling.LANCZOS)
    return ImageOps.pad(opaque, dimensions, method=Image.Resampling.LANCZOS, color='white')


class CoverMaker(ImageCompressor):
    def make(self, source, output_dir, platform='同时导出两种', framing='留白保留全图',
             size='标准尺寸', progress=lambda x: None):
        validate_cover_options(platform, framing, size)
        self.check_cancel()
        source, output_dir = Path(source).resolve(strict=True), Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        platforms = list(COVER_PRESETS) if platform == '同时导出两种' else [platform]
        pending, results = [], []
        try:
            with Image.open(source) as original:
                if getattr(original, 'n_frames', 1) > 1:
                    raise ValueError('不处理动图或多页图片，请先导出为单张图片。')
                image = ImageOps.exif_transpose(original)
                image.load()
                self.check_cancel()
                for index, name in enumerate(platforms):
                    cover = frame_cover(image, cover_dimensions(name, size), framing)
                    self.check_cancel()
                    # Try the best quality first; reduce quality only when necessary.
                    low, high, encoded = 10, 95, None
                    quality = high
                    while low <= high:
                        self.check_cancel()
                        buffer = io.BytesIO()
                        cover.save(buffer, format='JPEG', quality=quality, optimize=True, progressive=True)
                        if buffer.tell() <= COVER_LIMIT:
                            encoded = buffer.getvalue()
                            if quality == 95:
                                break
                            low = quality + 1
                        else:
                            high = quality - 1
                        quality = (low + high) // 2
                    if encoded is None:
                        raise ValueError(f'{name}封面无法压到 5 MB 以内，请选择最低尺寸。')
                    temporary = output_dir / f'.cover-{uuid.uuid4().hex}.tmp'
                    pending.append((temporary, name))
                    temporary.write_bytes(encoded)
                    progress((index + 1) / len(platforms) * .9)
            self.check_cancel()
            # Both versions are prepared before publishing either file.
            for temporary, name in pending:
                index = 0
                while True:
                    suffix = f'_{index}' if index else ''
                    target = output_dir / f'{source.stem}_{name}封面{suffix}.jpg'
                    try:
                        with target.open('xb'):
                            pass
                        results.append(target)
                        break
                    except FileExistsError:
                        index += 1
                temporary.replace(target)
            progress(1)
            return results
        except BaseException:
            for target in results:
                target.unlink(missing_ok=True)
            raise
        finally:
            for temporary, _ in pending:
                temporary.unlink(missing_ok=True)
