# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
from pathlib import Path
import time

from PIL import Image, ImageDraw
from app import App, messagebox

root = Path(__file__).parent / 'validation' / 'covers-ui'
root.mkdir(parents=True, exist_ok=True)
source = root / '封面样图.png'
image = Image.new('RGB', (700, 1000), '#DDE8ED')
draw = ImageDraw.Draw(image)
draw.rectangle((70, 70, 630, 930), fill='#32576B')
draw.ellipse((170, 230, 530, 590), fill='#D3B68B')
draw.rectangle((170, 640, 530, 700), fill='#F3E8D8')
image.save(source)
bad = root / '损坏.png'
bad.write_bytes(b'broken')
messagebox.showinfo = lambda *args: None
messagebox.showerror = lambda *args: (_ for _ in ()).throw(AssertionError(args))
app = App()
errors = []


def callback_error(kind, value, traceback):
    errors.append(value)
    app.destroy()


app.report_callback_exception = callback_error
app.image_limit.set('invalid')  # Compression settings must not affect cover exports.
app.switch_mode('封面制作')
app.add_paths([bad, source, source])
app.output.set(str(root / 'output'))
for mode in ('图片压缩', '视频倍速', '封面制作'):
    app.switch_mode(mode)
assert len(app.paths) == 2
assert app.output.get() == str(root / 'output')
deadline = time.monotonic() + 30


def start():
    app.start()
    assert app.busy
    assert app.controls[0].cget('state') == 'disabled'
    app.after(100, wait)


def wait():
    assert time.monotonic() < deadline, 'timeout'
    if app.busy:
        app.after(100, wait)
        return
    statuses = [app.tree.set(key, 'status') for key in app.paths]
    assert statuses[0].startswith('失败'), statuses
    assert statuses[1] == '完成 · 2 张封面', statuses
    assert app.last_log.is_file()
    assert '红果封面' in app.last_log.read_text(encoding='utf-8-sig')
    for platform, dimensions in [('红果', (700, 1000)), ('抖音', (960, 1440))]:
        results = list((root / 'output').glob(f'封面样图_{platform}封面*.jpg'))
        with Image.open(results[-1]) as image:
            assert image.size == dimensions
    assert app.start_btn.cget('state') == 'normal'
    app.switch_mode('视频倍速')
    app.switch_mode('封面制作')
    assert [app.tree.set(key, 'status') for key in app.paths] == statuses
    app.geometry('970x710')
    app.after(500, finish)


def finish():
    app.update_idletasks()
    assert app.winfo_width() == 970
    assert app.winfo_height() == 710
    app.destroy()


app.after(600, start)
app.mainloop()
if errors:
    raise errors[0]
print('Cover GUI: batch export, failure continuation, isolated settings, mode state and locking passed')
