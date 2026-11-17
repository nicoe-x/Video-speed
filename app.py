# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 nicoe-x
from __future__ import annotations

import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from image_core import ImageCompressor, IMAGE_EXTENSIONS, validate_image_options
from core import Cancelled, Converter, EXTENSIONS, binary, collect_folder, validate_speed

BG = '#F4F6FA'
INK = '#17243A'
MUTED = '#526176'
BLUE = '#245BE3'
ctk.set_appearance_mode('light')
ctk.set_default_color_theme('blue')


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('视频倍速工坊')
        self.geometry('1100x780')
        self.minsize(970, 710)
        self.configure(fg_color=BG)
        self.mode = '视频倍速'
        self.mode_state = {}
        self.image_quality = tk.StringVar(value='80')
        self.image_edge = tk.StringVar(value='0')
        self.image_format = tk.StringVar(value='自动（JPG/WebP）')
        self.image_limit = tk.StringVar(value='200')
        self.image_resize = tk.BooleanVar(value=False)
        self.image_width = tk.StringVar(value='')
        self.image_height = tk.StringVar(value='')
        self.image_aspect = tk.BooleanVar(value=True)
        self.paths = {}
        self.events = queue.Queue()
        self.converter = None
        self.busy = False
        self.scanning = False
        self.scan_cancel = threading.Event()
        self.closing = False
        self.last_log = None
        self.controls = []
        self.output = tk.StringVar()
        self.speed = tk.StringVar(value='2')
        self.quality = tk.StringVar(value='标准')
        self.mute = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=True)
        self._build()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def label(self, parent, text, size=14, color=INK, bold=False, **kwargs):
        return ctk.CTkLabel(parent, text=text, font=('Microsoft YaHei UI', size, 'bold' if bold else 'normal'), text_color=color, **kwargs)

    def button(self, parent, text, command, primary=False, width=110):
        widget = ctk.CTkButton(parent, text=text, command=command, width=width, height=38,
                               corner_radius=8, font=('Microsoft YaHei UI', 13),
                               fg_color=BLUE if primary else '#EAF0FF',
                               hover_color='#184BCB' if primary else '#DCE6FC',
                               text_color='white' if primary else '#254EAA')
        self.controls.append(widget)
        return widget

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.grid(row=0, column=0, sticky='ew', padx=28, pady=(22, 16))
        self.label(header, '视频倍速工坊', 27, bold=True).pack(side='left')
        modes = ctk.CTkSegmentedButton(header, values=['视频倍速', '图片压缩'], command=self.switch_mode,
                                       height=38, font=('Microsoft YaHei UI', 14), selected_color=BLUE,
                                       unselected_color=MUTED, fg_color=MUTED)
        modes.set(self.mode)
        modes.pack(side='right')
        self.controls.append(modes)
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.grid(row=1, column=0, sticky='nsew', padx=28)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, minsize=300)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color='white', corner_radius=14)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 16))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)
        self.count_label = self.label(left, f'01   添加{self.media_name}', 17, bold=True)
        self.count_label.grid(row=0, column=0, sticky='w', padx=20, pady=(18, 12))
        tools = ctk.CTkFrame(left, fg_color='transparent')
        tools.grid(row=1, column=0, sticky='ew', padx=20)
        self.button(tools, f'添加{self.media_name}', self.add_files, primary=True, width=104).pack(side='left', padx=(0, 8))
        self.button(tools, '添加文件夹', self.add_folder, width=112).pack(side='left')
        check = ctk.CTkCheckBox(left, text='导入文件夹时包含子文件夹', variable=self.recursive,
                              font=('Microsoft YaHei UI', 12), text_color=MUTED, checkbox_width=18, checkbox_height=18)
        check.grid(row=2, column=0, sticky='w', padx=20, pady=16)
        self.controls.append(check)
        table = ctk.CTkFrame(left, fg_color='#F8FAFD', corner_radius=0)
        table.grid(row=3, column=0, sticky='nsew', padx=20)
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('Video.Treeview', font=('Microsoft YaHei UI', 11), rowheight=40,
                        background='#F8FAFD', fieldbackground='#F8FAFD', foreground=INK, borderwidth=0)
        style.configure('Video.Treeview.Heading', font=('Microsoft YaHei UI', 11, 'bold'),
                        background='#EDF1F8', foreground=MUTED, relief='flat', padding=(8, 9))
        style.map('Video.Treeview', background=[('selected', '#DBE7FF')], foreground=[('selected', '#183C87')])
        self.tree = ttk.Treeview(table, columns=('name', 'size', 'status'), show='headings', style='Video.Treeview')
        for col, title, width in [('name', f'{self.media_name}文件', 280), ('size', '大小', 80), ('status', '状态', 112)]:
            self.tree.heading(col, text=title, anchor='w')
            self.tree.column(col, width=width, minwidth=65, stretch=col == 'name', anchor='w')
        if self.is_image:
            self.tree.column('size', width=150)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(table, orient='vertical', command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind('<<TreeviewSelect>>', self.show_path)
        self.tree.bind('<Delete>', lambda e: self.remove())
        self.path_hint = self.label(left, ('支持 JPG、PNG、WebP、BMP、TIFF' if self.is_image else '支持 MP4、MOV、MKV、AVI 等常用视频格式'), 11, MUTED, anchor='w')
        self.path_hint.grid(row=4, column=0, sticky='ew', padx=20, pady=(10, 4))
        cleanup = ctk.CTkFrame(left, fg_color='transparent')
        cleanup.grid(row=5, column=0, sticky='ew', padx=20, pady=(4, 16))
        self.button(cleanup, '移除选中', self.remove, width=100).pack(side='left', padx=(0, 8))
        self.button(cleanup, '清空列表', self.clear, width=100).pack(side='left')

        right = ctk.CTkScrollableFrame(body, fg_color='white', corner_radius=14, width=270,
                                      scrollbar_button_color='#CBD5E1')
        right.grid(row=0, column=1, sticky='nsew')
        right.grid_columnconfigure(0, weight=1)
        self.build_settings(right)
        self.label(right, '03   保存位置', 17, bold=True).grid(row=11 if self.is_image else 9, column=0, sticky='w', padx=20, pady=(8, 12))
        location = ctk.CTkEntry(right, textvariable=self.output, placeholder_text='添加文件后自动设置', height=36,
                               font=('Microsoft YaHei UI', 12))
        location.grid(row=12 if self.is_image else 10, column=0, sticky='ew', padx=20)
        self.controls.append(location)
        self.button(right, '选择保存文件夹', self.choose_output, width=260).grid(row=13 if self.is_image else 11, column=0, sticky='ew', padx=20, pady=(10, 12))
        self.label(right, ('原图保留 · 重名自动编号\n不处理动图或多页图片' if self.is_image else '统一导出为 MP4 · 原视频保留\n重名自动编号 · 全程本地处理'), 12, MUTED, justify='left').grid(row=14 if self.is_image else 12, column=0, sticky='w', padx=20, pady=(0, 18))

        footer = ctk.CTkFrame(self, fg_color='white', corner_radius=14)
        footer.grid(row=2, column=0, sticky='ew', padx=28, pady=(16, 22))
        footer.grid_columnconfigure(0, weight=1)
        self.status = self.label(footer, f'请添加需要处理的{self.media_name}。', 13, anchor='w', wraplength=500, justify='left')
        self.status.grid(row=0, column=0, sticky='ew', padx=20, pady=(14, 6))
        self.bar = ctk.CTkProgressBar(footer, progress_color=BLUE, fg_color='#E5EBF5', height=7)
        self.bar.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 16))
        self.bar.set(0)
        self.stop_btn = ctk.CTkButton(footer, text='停止', command=self.stop, width=70, height=42,
                                     fg_color='#EAF0FF', text_color=INK, state='disabled')
        self.stop_btn.grid(row=0, column=1, rowspan=2, padx=(0, 10))
        self.start_btn = ctk.CTkButton(footer, text='开始批量处理', command=self.start, width=155, height=44,
                                      fg_color=BLUE, hover_color='#184BCB', font=('Microsoft YaHei UI', 15, 'bold'))
        self.start_btn.grid(row=0, column=2, rowspan=2, padx=(0, 12))
        self.open_btn = ctk.CTkButton(footer, text='打开输出', command=self.open_output, width=90, height=42,
                                     fg_color='#EAF0FF', text_color=INK)
        self.open_btn.grid(row=0, column=3, rowspan=2, padx=(0, 20))

    @property
    def is_image(self):
        return self.mode == '图片压缩'

    @property
    def media_name(self):
        return '图片' if self.is_image else '视频'

    @property
    def extensions(self):
        return IMAGE_EXTENSIONS if self.is_image else EXTENSIONS

    def switch_mode(self, value):
        if self.busy or self.scanning or value == self.mode:
            return
        self.mode_state[self.mode] = (list(self.paths.values()), self.output.get(),
                                     {key: self.tree.item(key, 'values') for key in self.paths})
        self.mode = value
        self.paths = {}
        self.output.set('')
        self.controls = []
        for widget in self.winfo_children():
            widget.destroy()
        self._build()
        saved = self.mode_state.get(value)
        if saved:
            self.add_paths(saved[0])
            self.output.set(saved[1])
            for key, values in saved[2].items():
                self.tree.item(key, values=values)

    def build_settings(self, right):
        if self.is_image:
            self.label(right, '02   压缩设置', 17, bold=True).grid(row=0, column=0, sticky='w', padx=20, pady=(18, 12))
            for row, title, variable in ((2, '每张最大体积（KB，0 为不限）', self.image_limit),
                                         (4, '画质上限（10～95）', self.image_quality)):
                self.label(right, title, 13, MUTED).grid(row=row, column=0, sticky='w', padx=20)
                entry = ctk.CTkEntry(right, textvariable=variable, height=36, font=('Microsoft YaHei UI', 14))
                entry.grid(row=row+1, column=0, sticky='ew', padx=20, pady=(8, 16))
                self.controls.append(entry)
            self.label(right, '输出格式', 13, MUTED).grid(row=6, column=0, sticky='w', padx=20)
            option = ctk.CTkOptionMenu(right, values=['自动（JPG/WebP）', '原格式', 'JPEG', 'PNG', 'WebP'], variable=self.image_format,
                                      fg_color='#EAF0FF', button_color='#DCE6FC', text_color=INK, height=36)
            option.grid(row=7, column=0, sticky='ew', padx=20, pady=(8, 12))
            self.controls.append(option)
            resize = ctk.CTkCheckBox(right, text='允许缩小尺寸以满足体积', variable=self.image_resize,
                                     font=('Microsoft YaHei UI', 12), checkbox_width=18, checkbox_height=18)
            resize.grid(row=8, column=0, sticky='w', padx=20, pady=(0, 10))
            self.controls.append(resize)
            self.label(right, '默认保留像素尺寸，自动降低画质。\n压不到上限会提示，不保存超标文件。',
                       12, MUTED, justify='left').grid(row=9, column=0, sticky='w', padx=20, pady=(0, 12))
            resolution = ctk.CTkFrame(right, fg_color='transparent')
            resolution.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 14))
            self.label(resolution, '分辨率（宽 × 高，像素）', 13, MUTED).pack(anchor='w')
            inputs = ctk.CTkFrame(resolution, fg_color='transparent')
            inputs.pack(fill='x', pady=(8, 10))
            for variable, placeholder in ((self.image_width, '宽度'), (self.image_height, '高度')):
                entry = ctk.CTkEntry(inputs, textvariable=variable, placeholder_text=placeholder, width=105, height=36)
                entry.pack(side='left', padx=(0, 10))
                self.controls.append(entry)
            aspect = ctk.CTkCheckBox(resolution, text='保持比例', variable=self.image_aspect,
                                    font=('Microsoft YaHei UI', 12), checkbox_width=18, checkbox_height=18)
            aspect.pack(anchor='w')
            self.controls.append(aspect)
            self.label(resolution, '留空保留原尺寸；只填一边自动计算。\n同时填写时等比放入指定范围。\n关闭保持比例可强制宽高，可能变形。\n指定宽高后，不再为体积自动缩小。',
                       11, MUTED, justify='left').pack(anchor='w', pady=(8, 0))
            return
        self.label(right, '02   设置倍速', 17, bold=True).grid(row=0, column=0, sticky='w', padx=20, pady=(18, 12))
        self.label(right, '播放速度', 13, MUTED).grid(row=1, column=0, sticky='w', padx=20)
        speeds = ctk.CTkSegmentedButton(right, values=['0.5×', '1.5×', '2×', '4×'],
                                       command=lambda v: self.speed.set(v.replace('×', '')), height=36,
                                       font=('Microsoft YaHei UI', 12), selected_color=BLUE,
                                       fg_color=MUTED, unselected_color=MUTED, unselected_hover_color='#3C4B60')
        speeds.grid(row=2, column=0, sticky='ew', padx=20, pady=(8, 12))
        speeds.set('2×')
        self.controls.append(speeds)
        custom = ctk.CTkFrame(right, fg_color='transparent')
        custom.grid(row=3, column=0, sticky='ew', padx=20)
        self.label(custom, '自定义', 13).pack(side='left')
        entry = ctk.CTkEntry(custom, textvariable=self.speed, width=105, height=36, font=('Microsoft YaHei UI', 14))
        entry.pack(side='left', padx=(12, 8))
        self.label(custom, '倍').pack(side='left')
        self.controls.append(entry)
        self.label(right, '范围 0.25～16 倍；小于 1 为慢放', 11, MUTED).grid(row=4, column=0, sticky='w', padx=20, pady=(8, 16))
        self.label(right, '导出画质', 13, MUTED).grid(row=5, column=0, sticky='w', padx=20)
        option = ctk.CTkOptionMenu(right, values=['高画质', '标准', '小体积'], variable=self.quality,
                                  fg_color='#EAF0FF', button_color='#DCE6FC', button_hover_color='#CBDCFA',
                                  text_color=INK, height=36, font=('Microsoft YaHei UI', 13))
        option.grid(row=6, column=0, sticky='ew', padx=20, pady=(8, 18))
        self.controls.append(option)
        switch = ctk.CTkSwitch(right, text='静音导出', variable=self.mute, font=('Microsoft YaHei UI', 13), text_color=INK)
        switch.grid(row=7, column=0, sticky='w', padx=20)
        self.controls.append(switch)
        self.label(right, '默认保留声音，并尽量保持原音调。', 11, MUTED).grid(row=8, column=0, sticky='w', padx=20, pady=(8, 18))

    def set_locked(self, locked):
        for widget in self.controls:
            widget.configure(state='disabled' if locked else 'normal')
        self.start_btn.configure(state='disabled' if locked else 'normal')
        self.stop_btn.configure(state='normal' if locked else 'disabled')

    def add_files(self):
        files = filedialog.askopenfilenames(title=f'选择{self.media_name}（可多选）', filetypes=[(f'{self.media_name}文件', ' '.join('*' + e for e in sorted(self.extensions))), ('所有文件', '*.*')])
        self.add_paths(files)

    def add_paths(self, files):
        added = 0
        for file in files:
            path = Path(file).resolve()
            key = os.path.normcase(str(path))
            if key in self.paths or path.suffix.lower() not in self.extensions or not path.is_file():
                continue
            try:
                size = path.stat().st_size / 1024**2
            except OSError:
                continue
            self.paths[key] = path
            size_text = f'{size * 1024:.1f} KB' if size < 1 else f'{size:.1f} MB'
            self.tree.insert('', 'end', iid=key, values=(path.name, size_text, '待处理'))
            added += 1
            if not self.output.get():
                self.output.set(str(path.parent / ('图片压缩输出' if self.is_image else '倍速输出')))
        self.count_label.configure(text=f'01   {self.media_name}列表 · {len(self.paths)} 个')
        self.status.configure(text=f'已添加 {added} 个{self.media_name}，共 {len(self.paths)} 个。')

    def add_folder(self):
        folder = filedialog.askdirectory(title=f'选择{self.media_name}文件夹')
        if not folder:
            return
        recursive = self.recursive.get()
        excluded = Path(self.output.get()) if self.output.get().strip() else None
        self.scanning = True
        self.scan_cancel.clear()
        self.set_locked(True)
        self.status.configure(text='正在扫描文件夹…')
        def scan():
            try:
                files = collect_folder(Path(folder), recursive, excluded, self.scan_cancel, self.extensions)
                self.events.put(('scan', files, None))
            except Cancelled:
                self.events.put(('scan', [], '扫描已停止。'))
            except Exception as exc:
                self.events.put(('scan', [], str(exc)))
        threading.Thread(target=scan, daemon=True).start()

    def show_path(self, _=None):
        selected = self.tree.selection()
        if selected:
            text = str(self.paths[selected[0]])
            self.path_hint.configure(text=text if len(text) < 68 else '…' + text[-67:])

    def remove(self):
        if self.busy or self.scanning:
            return
        for key in self.tree.selection():
            self.paths.pop(key, None)
            self.tree.delete(key)
        self.count_label.configure(text=f'01   {self.media_name}列表 · {len(self.paths)} 个')

    def clear(self):
        if self.busy or self.scanning:
            return
        self.tree.delete(*self.tree.get_children())
        self.paths.clear()
        self.count_label.configure(text=f'01   添加{self.media_name}')
        self.status.configure(text=f'列表已清空，请添加{self.media_name}。')

    def choose_output(self):
        folder = filedialog.askdirectory(title='选择保存文件夹')
        if folder:
            self.output.set(folder)

    def open_output(self):
        path = Path(self.output.get()) if self.output.get().strip() else None
        if path and path.is_dir():
            os.startfile(str(path.resolve()))
        else:
            messagebox.showinfo('保存位置', '请先选择有效的保存文件夹。')

    def start(self):
        if self.busy or self.scanning:
            return
        try:
            if not self.paths:
                raise ValueError(f'请先添加{self.media_name}或文件夹。')
            image_options = validate_image_options(self.image_quality.get(), 0, self.image_format.get(),
                                                  self.image_limit.get(), self.image_resize.get(),
                                                  self.image_width.get(), self.image_height.get(), self.image_aspect.get()) if self.is_image else None
            speed = 1 if self.is_image else validate_speed(self.speed.get().strip())
            if not self.output.get().strip():
                raise ValueError('请选择保存文件夹。')
            output = Path(self.output.get().strip()).expanduser().resolve()
            output.mkdir(parents=True, exist_ok=True)
            if not self.is_image:
                binary('ffmpeg')
                binary('ffprobe')
        except (ValueError, OSError, RuntimeError) as exc:
            messagebox.showerror('无法开始', str(exc))
            return
        self.output.set(str(output))
        self.busy = True
        self.set_locked(True)
        self.bar.set(0)
        self.converter = ImageCompressor() if self.is_image else Converter()
        items = list(self.paths.items())
        for key, _ in items:
            self.tree.set(key, 'status', '等待中')
        self.status.configure(text=f'正在准备 {len(items)} 个{self.media_name}…')
        threading.Thread(target=self.work, args=(items, output, speed, self.mute.get(), self.quality.get(), image_options), daemon=True).start()

    def work(self, items, output, speed, mute, quality, image_options=None):
        success, failed, report = 0, 0, []
        total = len(items)
        for index, (key, path) in enumerate(items):
            if self.converter.cancelled.is_set():
                break
            self.events.put(('item', key, '处理中'))
            self.events.put(('status', f'正在处理 {index + 1}/{total}：{path.name}'))
            try:
                update = lambda value, i=index: self.events.put(('progress', (i + value) / total))
                if image_options is not None:
                    result = self.converter.compress(path, output, progress=update, **image_options)
                    before, after = path.stat().st_size, result.stat().st_size
                    ratio = (1 - after / before) * 100 if before else 0
                    item_status = f'完成 · 减少 {ratio:.0f}%' if ratio >= 0 else f'完成 · 增大 {-ratio:.0f}%'
                    report.append(f'大小：{before} → {after} 字节\n')
                    self.events.put(('size', key, f'{before/1024:.0f} → {after/1024:.0f} KB'))
                else:
                    result = self.converter.convert(path, output, speed, mute, quality, update)
                    item_status = '已完成'
                success += 1
                report.append(f'成功：{path}\n保存：{result}\n')
                self.events.put(('item', key, item_status))
            except Cancelled:
                self.events.put(('item', key, '已停止'))
                break
            except Exception as exc:
                failed += 1
                report.append(f'失败：{path}\n原因：{exc}\n')
                self.events.put(('item', key, '失败（见日志）'))
            self.events.put(('progress', (index + 1) / total))
        stopped = self.converter.cancelled.is_set()
        log_error = ''
        try:
            from datetime import datetime
            log = output / f'处理记录_{datetime.now():%Y%m%d_%H%M%S_%f}.txt'
            settings = f'图片压缩：{image_options}' if image_options is not None else f'倍速：{speed:g}x'
            log.write_text(f'{settings}\n成功 {success}，失败 {failed}，未完成 {total-success-failed}\n\n' + '\n'.join(report), encoding='utf-8-sig')
        except OSError as exc:
            log = None
            log_error = f'\n日志未能保存：{exc}'
        self.events.put(('done', success, failed, stopped, total, log, log_error))

    def stop(self):
        if self.scanning:
            self.scan_cancel.set()
        if self.busy and self.converter:
            self.converter.cancel()
        self.stop_btn.configure(state='disabled')
        self.status.configure(text='正在停止，已完成的文件会保留…')

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == 'progress':
                    self.bar.set(event[1])
                elif kind == 'item':
                    self.tree.set(event[1], 'status', event[2])
                    self.tree.see(event[1])
                elif kind == 'size':
                    self.tree.set(event[1], 'size', event[2])
                elif kind == 'status':
                    self.status.configure(text=event[1])
                elif kind == 'scan':
                    self.scanning = False
                    self.set_locked(False)
                    if not self.closing:
                        self.add_paths(event[1])
                        if event[2]:
                            self.status.configure(text=event[2])
                elif kind == 'done':
                    _, success, failed, stopped, total, self.last_log, log_error = event
                    self.busy = False
                    self.set_locked(False)
                    for key in self.paths:
                        if self.tree.set(key, 'status') == '等待中':
                            self.tree.set(key, 'status', '未处理')
                    summary = f'{"已停止" if stopped else "处理结束"}：成功 {success} 个，失败 {failed} 个，未完成 {total-success-failed} 个。'
                    self.status.configure(text=summary)
                    if not self.closing:
                        detail = summary + '\n\n文件已保存到：\n' + self.output.get()
                        if failed:
                            detail += '\n\n失败原因请查看输出文件夹内的“处理记录”文件。'
                        messagebox.showinfo('批量处理', detail + log_error)
        except queue.Empty:
            pass
        if self.closing and not self.busy and not self.scanning:
            self.destroy()
            return
        self.after(100, self.poll)

    def close(self):
        if self.busy or self.scanning:
            if not messagebox.askyesno('退出软件', '正在处理，是否停止后退出？已完成的文件会保留。'):
                return
            self.closing = True
            self.stop()
        else:
            self.destroy()


if __name__ == '__main__':
    App().mainloop()
