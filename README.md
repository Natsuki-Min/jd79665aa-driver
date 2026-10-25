# JD79665AA driver & reverse-engineering notes

**SE0398NZ07A1 · 3.98 英寸四色电子纸 · RP2040 / Raspberry Pi Pico**

Minimal RP2040 driver and reverse-engineering notes for the **JD79665AA / A1** controller on a **SE0398NZ07A1** four-color e-paper panel. Includes the R20 LUT byte codec, an offline MTP LZ decoder, and two extracted waveform tables. Documentation is primarily in Chinese.

本仓库从实板实验中整理出一套可独立使用的资料：**原厂四色全刷驱动、R20 波形编码说明，以及可复现的 MTP 解码工具和样本数据**。驱动针对物理 800 × 600、可见 768 × 552 的面板，图像为 2bpp 黑、白、黄、红。

当前最完整的逆向结果是：从 4096 B MTP 样本中解出 LZ 压缩流和两张 **535 B** 状态表。其中 profile 1 与历史 742 扫描实测的已辨识位一致；完整表块尚未回灌做光学复现。详见 [MTP 解码说明](docs/05-mtp.md)。

## 支持范围

| 项目 | 已有结果 | 验证方式 |
| --- | --- | --- |
| 原厂四色全刷 | 正常显示；DRF 约 15.2 s，含传输的一次完整更新约 16–17 s | 历史实板验证 |
| R83 窗口 | 可见坐标到镜像编码坐标的映射；提供窗口更新 API | 历史 R93 RAM 回读；不保证窗口外光学隔离 |
| R20 自定义波形编码 | 字节映射、11 B 状态、六条入口、两层重复及扫描数模型 | 历史 BUSY/VSL 测量；附离线编解码工具 |
| MTP 解码 | 两张 535 B 表，六轨分别各 1399 / 742 扫描 | 随仓库样本可离线复现 |
| R93 图像 RAM 回读 | 历史 120000 B 全帧回读与发送内容零差异 | 回读实现未包含在最小驱动中 |

**完整原厂波形回灌、MTP 温区选表、绝对电压标定、长期寿命和高速视频画质仍未解决。** 历史实验曾达到 24 fps 级别，但不代表具备合格的视频显示效果；视频引擎未收入本仓库。

## 快速开始

以下命令均从本仓库根目录执行。若使用原实验仓库中的副本，先进入 `share/`。

### 离线复现（无需硬件）

需要 **Python 3.9 或更新版本**，仅使用标准库：

```sh
python3 host/selftest.py
python3 host/decode_mtp.py
python3 host/show_profile.py --lane 5
(cd data && sha256sum -c SHA256SUMS)
```

预期得到 11510 B 解压输出、534 个 token，以及六轨各 1399 / 742 扫描的两张表。工具不会打开串口或访问面板，原始样本及哈希见 [data/README.md](data/README.md)。

### 构建 Pico 驱动

先按[接线说明](docs/01-panel-and-wiring.md)连接原面板 PCB 与 Pico。构建需要 CMake、Ninja、Arm GNU Toolchain、Pico SDK 和 picotool。本机已用 Pico SDK 2.3.1 / GCC 15.2.1 构建通过：

```sh
./driver/build.sh
```

脚本会尝试原开发环境的 `~/.pico-sdk/` 路径。其他机器可显式指定：

```sh
./driver/build.sh \
  -DPICO_SDK_PATH=/path/to/pico-sdk \
  -DPICO_TOOLCHAIN_PATH=/path/to/arm-toolchain \
  -Dpicotool_DIR=/path/to/picotool-cmake-package
```

`picotool_DIR` 应指向包含 `picotoolConfig.cmake` 的目录。SDK 需要其构建依赖的子模块（包括 TinyUSB）。

生成 `driver/build/epd_bringup.uf2`。按住 Pico 的 BOOTSEL 接入 USB，将 UF2 复制到 `RPI-RP2`。程序在上电后画黑、白、黄、红四条竖带，再关闭面板高压；USB 串口输入 `r` 重画、`s` 查看状态。此步骤会写 Pico Flash，不写面板 MTP/OTP。

完整操作见 [driver/README.md](driver/README.md)，本次软件验证记录见 [docs/07-validation.md](docs/07-validation.md)。

## 目录与阅读顺序

```text
.
├── driver/       Pico 最小驱动与构建脚本
├── host/         无第三方依赖的 Python 编解码、解表和自检工具
├── data/         4096 B MTP 样本、四个表文件和 SHA256SUMS
├── docs/         协议说明、波形图、已知限制和验证记录
└── NOTICE.md     来源与许可状态
```

1. [面板、接线与图像格式](docs/01-panel-and-wiring.md)
2. [初始化与全刷](docs/02-init-and-refresh.md)
3. [R83 窗口与镜像坐标](docs/03-image-and-window.md)
4. [R20 波形表编码](docs/04-lut.md)
5. [MTP 压缩流与两张状态表](docs/05-mtp.md)
6. [实验边界、负结果与安全](docs/06-limits-and-safety.md)
7. [软件验证记录与复现命令](docs/07-validation.md)

## 常用术语

| 术语 | 含义 |
| --- | --- |
| R20 | 写寄存器 LUT 的命令；实验中使用 2048 B 地址空间 |
| H0–H5 | 状态表的六条入口，首状态偏移为 `7 + 88 × H` |
| R83 | 窗口命令；本面板 X 坐标需要镜像补偿 |
| DRF | 刷新命令 `0x12` |
| logical / wire | 解码后的逻辑字节 / 经 SPI 发送给 R20 的编码字节 |
| G / RA / RB | 外层重复 / ABC 子组重复 / DEF 子组重复 |
| profile 0 / 1 | 解出的两张表；尚未证实其温度档位和选择规则 |

## 来源与使用边界

初始化和全刷序列移植自 `krstc/openepaperlinkforCN` 的固定版本，并与另一份实现交叉核对。来源链接、提交号及许可状态见 [NOTICE.md](NOTICE.md)。本仓库暂未声明统一开源许可证。

样本与历史测量来自**同一块面板**，其他批次、温度或 FPC 需要重新验证。`data/mtp.bin` 包含该面板的工厂数据/标识，不是通用固件；解出的 535 B 表块也不是完整、已验证的 2048 B R20 payload。请勿写面板 MTP/OTP。

完整实验仓库中的视频引擎、相机闭环、搜索日志、厂商 PDF 和第三方源码副本未收入本仓库。文中明确标注的历史实测结论来自原实验记录；随本仓库可直接复现的是数据解码、字节映射与软件构建。
