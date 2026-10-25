# JD79665AA driver & reverse-engineering notes

**SE0398NZ07A1 · 3.98 英寸四色电子纸 · RP2040 / Raspberry Pi Pico**

RP2040 driver, R20 waveform LUT format and MTP LZ decoder for the **JD79665AA / A1** controller on a **SE0398NZ07A1** four-color e-paper panel. Includes waveform data and experiments on fast refresh, ghosting and image history. Documentation is primarily in Chinese.

这份资料面向拿到同类屏幕、想移植驱动或研究波形的人。仓库提供能显示四色测试图的 Pico 驱动，说明图像如何写入、刷新窗口如何定位、波形表如何编码，并附上可运行的 MTP 解码器和样本。

理解这个控制器时，最有用的区分是：**图像数据指定像素的类别，波形表指定这类像素接下来经历的电压序列。** 原厂模式用内置波形显示黑、白、黄、红；自定义波形则让同样的像素码选择自己定义的驱动过程。调整刷新速度和研究残影，主要是在改后者。

## 你能从这里得到什么

| 要做的事 | 可以直接复用的内容 |
| --- | --- |
| 把屏幕驱动起来 | [接线与 2bpp 格式](docs/01-panel-and-wiring.md)、[初始化字节和全刷流程](docs/02-init-and-refresh.md)、[Pico C 驱动](driver/README.md) |
| 在指定位置更新图像 | [R83 窗口的坐标换算、紧排数据格式和示例](docs/03-image-and-window.md) |
| 编写或分析波形 | [R20 字节映射、六路时序、11 B 状态和重复规则](docs/04-lut.md)、[Python 编解码工具](host/README.md) |
| 研究原厂波形 | [MTP 的 LZ 格式与两张 535 B 表](docs/05-mtp.md)、[原始样本与实测对照数据](data/README.md) |
| 继续探索快刷 | [实验路线与结果](docs/06-refresh-experiments.md)：为什么尝试、如何对照、观察到了什么，以及哪些思路仍有空间 |

第一次接触这套资料，建议先读 [整体工作方式](docs/00-overview.md)。它解释 MCU、图像 RAM、LUT 和 MTP 的关系，以及“扫描”“刷新”“视频帧”的区别。

## 先运行一个例子

以下命令从本仓库根目录执行。

### 无需硬件：解出原厂表

需要 Python 3.9 或更新版本，仅使用标准库：

```sh
python3 host/selftest.py
python3 host/decode_mtp.py
python3 host/show_profile.py --lane 5
```

`decode_mtp.py` 从 `data/mtp.bin` 解出 11510 B 数据，其中开头是两张 535 B 状态表。两张表的六路总扫描数分别为 1399 和 742；`show_profile.py` 可以查看每一路的相位和重复数。profile 1 与此前通过控制器计时恢复的字段相符，验证方法见 [MTP 章节](docs/05-mtp.md)。

### 有硬件：显示四色测试图

按[接线说明](docs/01-panel-and-wiring.md)连接 Pico 和面板 PCB，准备 CMake、Ninja、Arm GNU Toolchain、Pico SDK 和 picotool，然后运行：

```sh
./driver/build.sh
```

脚本会查找原开发环境的 `~/.pico-sdk/` 路径。其他环境可以指定工具位置：

```sh
./driver/build.sh \
  -DPICO_SDK_PATH=/path/to/pico-sdk \
  -DPICO_TOOLCHAIN_PATH=/path/to/arm-toolchain \
  -Dpicotool_DIR=/path/to/picotool-cmake-package
```

`picotool_DIR` 指向含 `picotoolConfig.cmake` 的目录。按住 Pico 的 BOOTSEL 接入 USB，将生成的 `driver/build/epd_bringup.uf2` 复制到 `RPI-RP2`。上电后显示黑、白、黄、红四条竖带；USB 串口输入 `r` 重画、`s` 查看状态。完整更新约 16–17 秒，其中原厂波形约 15.2 秒。

这个例子演示的是控制器协议。移植到其他 MCU 时，主要替换 GPIO、SPI、延时和 BUSY 等待接口；接线和构建细节见 [driver/README.md](driver/README.md)。

## 资料结构

```text
.
├── driver/       Pico 驱动与测试图程序
├── host/         Python 波形编解码、MTP 解码与自检
├── data/         MTP 样本、解出的波形表和独立实测字段对照
├── docs/         从工作原理到字节格式，再到快刷实验的说明
└── NOTICE.md     代码、文档与数据来源
```

按顺序阅读：[整体工作方式](docs/00-overview.md) → [面板与图像](docs/01-panel-and-wiring.md) → [初始化与全刷](docs/02-init-and-refresh.md) → [窗口](docs/03-image-and-window.md) → [波形编码](docs/04-lut.md) → [MTP 解码](docs/05-mtp.md) → [快刷实验](docs/06-refresh-experiments.md)。[软件复现记录](docs/07-validation.md)列出了自检内容和构建环境。

格式和实验数据来自一块 SE0398NZ07A1 面板；需要跨硬件核对的主要是初始化参数、电压配置和 MTP 选表规则。文中把已测行为、文件解码结果和待验证解释分别说明，方便移植时判断哪些可以沿用。完整表块的回灌显示、温区选择和长期光学表现仍是可继续研究的项目。

初始化序列的上游来源、提交号及当前许可状态见 [NOTICE.md](NOTICE.md)。
