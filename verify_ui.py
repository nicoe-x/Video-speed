# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
"""Exercise the real Tk event loop with generated input and capture our window."""
from pathlib import Path
import subprocess
import time

from app import App, messagebox
from core import HIDDEN, binary

root = Path(__file__).parent / 'validation'
root.mkdir(exist_ok=True)
source = root / '演示视频.mp4'
if not source.exists():
    subprocess.run([binary('ffmpeg'), '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=640x360:rate=30',
                    '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '6',
                    '-c:v', 'libx264', '-c:a', 'aac', str(source)], check=True, **HIDDEN)
bad = root / '损坏文件.mp4'
bad.write_text('invalid')
messages = []
messagebox.showinfo = lambda *args: messages.append(args)
messagebox.showerror = lambda *args: messages.append(args)
app = App()
app.output.set(str(root / 'output'))
app.add_paths([bad, source, source])
assert len(app.paths) == 2
app.lift()

def capture():
    app.update_idletasks()
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    code = f'from PIL import ImageGrab; ImageGrab.grab(bbox={x,y,x+w,y+h}).save({str(root / "界面预览.png")!r})'
    subprocess.run(['python', '-c', code], check=True, **HIDDEN)
    app.start()

deadline = time.monotonic() + 40

def wait():
    if time.monotonic() > deadline:
        app.stop()
        app.destroy()
        raise RuntimeError('GUI test timeout')
    if app.busy:
        app.after(100, wait)
        return
    statuses = [app.tree.set(key, 'status') for key in app.paths]
    assert statuses == ['失败（见日志）', '已完成'], statuses
    assert app.start_btn.cget('state') == 'normal'
    assert app.last_log and app.last_log.is_file()
    assert messages
    print('GUI batch OK: deduplication, failure continuation, completion, log, control unlock')
    app.destroy()

app.after(1000, capture)
app.after(1500, wait)
app.mainloop()
