# 视频倍速工坊

批量给视频调倍速的 Windows 小工具。把视频加进列表，选好速度和保存位置，点一次开始就能依次处理。原文件保留，结果另存为 MP4。

支持 Windows 10 / 11（64 位），视频都在本机处理。

## 怎么用

点击「添加视频」可以一次选多个文件，也可以直接添加整个文件夹。文件夹默认连同子目录一起扫描，重复文件只添加一次。

倍速范围是 0.25～16。比如一段 10 分钟的视频，设为 2 倍速，处理后大约是 5 分钟；设为 0.5 倍速，就是慢放到大约 20 分钟。默认保留声音，也可以打开「静音导出」。

没有改保存位置的话，结果会放在第一个视频旁边的「倍速输出」文件夹里。文件名会带上倍速，重名时自动加编号。

详细操作见 [使用说明](使用说明.md)。

## 从源码运行

需要 Python 3.13、FFmpeg 和 FFprobe。先确认终端能运行 `ffmpeg -version` 和 `ffprobe -version`。Windows 的 FFmpeg 可以从 [Gyan builds](https://www.gyan.dev/ffmpeg/builds/) 下载，仓库里没有附带这些程序。

在 PowerShell 里执行：

```powershell
git clone https://github.com/nicoe-x/Video-speed.git
cd Video-speed
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## 打包

装好上面的依赖后运行：

```powershell
.\build.ps1
```

打包结果在 `dist/视频倍速工坊/`，里面的 EXE 可以直接运行。拷贝给别人时，要把整个文件夹一起带上，包括 `_internal` 和许可证文件。便携版自带 Python 运行环境及 FFmpeg。

脚本按 Gyan essentials 的目录结构收集 FFmpeg 许可证：`bin` 文件夹里放程序，上一级放 `LICENSE`。如果用的是其他构建，请调整 `build.ps1` 中对应的路径。

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_conversion
```

测试会临时生成视频，检查倍速、音画时长、静音、重名保存、取消任务和损坏文件等情况。

界面测试用 `verify_ui.py`，需要 Windows 桌面环境。截图还需要系统 `python` 装有 Pillow：`python -m pip install Pillow`。测试文件和截图保存在 `validation/`，不会提交到仓库。

## 几个需要注意的地方

调倍速要重新编码，画质和文件大小会有变化。输出使用 H.264 / AAC，最高 60fps；慢放靠重复画面实现，没有插帧。

带多条音轨的视频会保留音轨，但只导出第一路普通视频画面，不带字幕和章节。HDR、杜比视界素材的颜色可能变化，建议先试一段。

点击停止会取消当前文件，已经处理好的文件会保留。再次开始会重跑整个列表，想单独重试几个文件的话，先把其他文件从列表移除。

## 许可证

代码和文档采用 [Apache-2.0](LICENSE)。Copyright 2026 nicoe-x。

FFmpeg 等第三方软件使用各自的许可证。便携版采用的 Gyan essentials 构建使用 GPLv3，具体来源见 [第三方声明](THIRD_PARTY_NOTICES.txt)。
