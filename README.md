# Video Speed · 视频倍速工坊

用于 Windows 10/11 64 位的本地视频批量倍速工具。选择视频或文件夹，设置统一倍速，即可批量处理并保存为 MP4。所有处理在本机完成，无需账号或网络服务。

## 功能

- 批量添加视频、导入文件夹，可包含子文件夹并自动去重。
- 支持 **0.25～16 倍速**，提供常用倍速快捷选项。
- 默认保留音轨并尽量保持音调，可选择静音导出。
- 高画质、标准、小体积三种编码质量。
- 可选择保存目录，原视频保留，同名输出自动编号。
- 进度显示、中途停止、失败后继续处理及处理日志。

支持 MP4、MOV、MKV、AVI、WMV、FLV、WebM、M4V、MTS、M2TS 等 FFmpeg 可解码的视频文件。输出为 H.264 / AAC 编码的 MP4。

## 从源码运行

安装 Python 3.13，以及可从 PATH 调用的 `ffmpeg` 和 `ffprobe`。FFmpeg 可从 [FFmpeg 官网](https://ffmpeg.org/download.html) 获取，Windows 构建可参考 [Gyan builds](https://www.gyan.dev/ffmpeg/builds/)。本仓库不包含 FFmpeg 二进制文件。

在 PowerShell 中运行：

```powershell
git clone https://github.com/nicoe-x/Video-speed.git
cd Video-speed
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

使用方式：**添加视频 / 文件夹 → 设置倍速 → 选择保存位置 → 开始批量处理**。

默认输出至第一个视频所在文件夹的「倍速输出」目录。已完成文件会保留；停止时删除正在处理的临时文件。

## 打包 Windows 便携版

完成上面的环境准备后，在 PowerShell 中运行：

```powershell
.\build.ps1
```

输出位于 `dist/视频倍速工坊/`。双击该文件夹中的 EXE 即可使用，无需另外安装 Python 或 FFmpeg。发布时请分发完整文件夹，保留 `_internal`、许可文件及第三方声明。

打包脚本从 PATH 获取 FFmpeg 和 FFprobe，并从其安装目录的上一级复制 `LICENSE`，适用于 Gyan essentials 的目录结构。其他来源的 FFmpeg 构建需要相应调整许可证收集路径。分发第三方工具时，须遵守该构建及其依赖的许可条件。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_conversion
```

测试自动生成短视频，验证倍速与音画时长、静音与无音轨输入、重名保护、取消清理、异常文件和文件夹扫描。不会使用个人视频。

`verify_ui.py` 另提供桌面交互流程验证，需要真实 Windows 桌面。其截图步骤需要系统 `python` 安装 Pillow（`python -m pip install Pillow`）。测试产物写入被 Git 忽略的 `validation/` 文件夹。

## 范围与限制

- 倍速处理会重新编码，文件体积和画质可能变化。
- 导出第一路普通视频画面及所有可解码音轨；不导出字幕、章节及额外视频轨。
- 帧率上限为 60fps；慢放使用重复画面，不进行运动插帧。
- 输出为 8 位编码，HDR / 杜比视界素材不保证保持原有色彩，建议先验证效果。
- 再次开始会重新处理整个列表；重试部分文件前可移除其他项目。

更多说明见 [使用说明](使用说明.md)。

## 开源许可

本项目原创源码与文档使用 **[Apache License 2.0](LICENSE)**，Copyright 2026 nicoe-x。

第三方软件保留各自许可证。FFmpeg 通过独立子进程调用；本地便携版所使用的 Gyan essentials 构建为 GPLv3，不因本项目的 Apache-2.0 许可而变更许可。第三方来源及说明见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
