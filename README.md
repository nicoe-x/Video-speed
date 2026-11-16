# Video-speed

Windows 视频批量倍速工具。

- 添加多个视频或整个文件夹，支持子目录。
- 倍速范围 0.25～16，可保留声音或静音。
- 结果另存为 MP4，原文件不变，重名自动编号。

添加视频，设置倍速和保存位置，点击「开始批量处理」。操作说明见 [使用说明](使用说明.md)。

## 运行

环境：Windows 10 / 11 x64、Python 3.13。`ffmpeg` 和 `ffprobe` 需加入 PATH，可从 [Gyan](https://www.gyan.dev/ffmpeg/builds/) 下载。

```powershell
git clone https://github.com/nicoe-x/Video-speed.git
cd Video-speed
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## 打包

```powershell
.\build.ps1
```

输出文件：`dist/视频倍速工坊.exe`。Python、FFmpeg 和 FFprobe 已打包进去，可单独运行。首次启动需要解压到系统临时目录，可能稍慢。

许可证和说明同时生成在 `dist/许可证与说明.zip`，EXE 内也保留一份。

脚本按 Gyan essentials 的目录结构复制 FFmpeg 许可证：程序在 `bin/`，`LICENSE` 在其上一级。使用其他构建时需修改对应路径。

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_conversion
```

测试视频由脚本生成。界面测试见 `verify_ui.py`，需 Windows 桌面及系统 Python 安装 Pillow。

## 许可

[Apache-2.0](LICENSE) · Copyright 2026 nicoe-x

第三方组件保留各自许可。便携版中的 Gyan FFmpeg 构建采用 GPLv3，见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
