# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
from pathlib import Path
import time
from PIL import Image, ImageGrab
from app import App, messagebox

root = Path(__file__).parent / 'validation' / 'images-ui'
root.mkdir(parents=True, exist_ok=True)
source = root / '照片.jpg'
Image.effect_noise((1200, 800), 60).convert('RGB').save(source, quality=98)
bad = root / '损坏.png'
bad.write_bytes(b'broken')
messagebox.showinfo = lambda *args: None
messagebox.showerror = lambda *args: (_ for _ in ()).throw(AssertionError(args))
app = App()
app.switch_mode('图片压缩')
app.add_paths([bad, source, source])
app.output.set(str(root / 'output'))
app.switch_mode('视频倍速')
assert not app.paths
app.switch_mode('图片压缩')
assert len(app.paths) == 2
assert app.output.get() == str(root / 'output')
deadline = time.monotonic() + 30

def start():
    app.update_idletasks()
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    ImageGrab.grab(bbox=(x,y,x+w,y+h)).save(root/'图片压缩界面.png')
    app.start()
    assert app.busy
    assert app.controls[0].cget('state') == 'disabled'
    app.after(100, wait)

def wait():
    if time.monotonic() > deadline:
        raise AssertionError('timeout')
    if app.busy:
        app.after(100, wait)
        return
    statuses = [app.tree.set(k, 'status') for k in app.paths]
    assert statuses[0].startswith('失败'), statuses
    assert statuses[1].startswith('完成'), statuses
    assert app.last_log.is_file()
    assert app.start_btn.cget('state') == 'normal'
    app.switch_mode('视频倍速')
    app.switch_mode('图片压缩')
    assert [app.tree.set(k, 'status') for k in app.paths] == statuses
    app.destroy()
    print('Image GUI batch, failure continuation, mode state and control locking passed')

app.after(600, start)
app.mainloop()
