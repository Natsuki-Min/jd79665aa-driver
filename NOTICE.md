# 来源、署名与许可

## 驱动代码

`driver/src/epd.c` 的初始化/全刷序列移植自：

- [krstc/openepaperlinkforCN · jd79665.cpp](https://github.com/krstc/openepaperlinkforCN/blob/42bd21471b5d3a6df07fd5ff9639fb88b5bcdc11/tag_fw/src/epd_driver/jd79665.cpp)，commit `42bd21471b5d3a6df07fd5ff9639fb88b5bcdc11` 的 `epdSetup()`、`epdWriteDisplayDataPhysicalFrame()`、`drawNoWait()`、`powerOff()`；
- 并和 [EPD_3in98g.cpp](https://github.com/krstc/openepaperlinkforCN/blob/42bd21471b5d3a6df07fd5ff9639fb88b5bcdc11/refdoc/BLE_EPD_DISPLAY/EPD_3in98g.cpp)、[panyihang/3.98Inch-ESP32C3-EPD · epd_panel.c](https://github.com/panyihang/3.98Inch-ESP32C3-EPD/blob/779eab27ba8b914e097fec530d1e1d601265fdcc/main/epd_panel.c)（commit `779eab27ba8b914e097fec530d1e1d601265fdcc`）交叉核对过。

移植文件头保留了来源项目、提交号和函数名。整理时，本地保存的 `openepaperlinkforCN` 参考版本未发现仓库级 LICENSE，`jd79665.cpp` 本身也未声明许可证；另一份 ESP32-C3 参考文件标注 `Unlicense OR CC0-1.0`，这不代表它能替前者授权。**本仓库不为上游重新声明许可证，也不将“源码可见”视为已获得统一开源授权。** 再分发或用于其他项目时，请核对相应来源的授权状态。

`driver/pico_sdk_import.cmake` 是 Raspberry Pi Pico SDK 的 BSD-3-Clause 副本，文件内保留了版权和许可全文。

## 文档、解码结果与数据

`docs/`、`host/`、`data/` 里的整理文字、解码器、状态表和 `mtp.bin` 来自本项目的实验工作。除第三方代码外，本仓库**暂未声明统一的开源许可证**。保留本 NOTICE 和来源说明并不自动构成对任意复用、修改或再分发的授权。

`data/mtp.bin` 是从这一块 SE0398NZ07A1 面板读出的 4096 B MTP 内容。它包含该样本的工厂数据/标识（例如 `CJ1TM`、`NK863`），随仓库原样保留以便核验解码结果；这些内容的完整用途尚未确认。它不是通用固件，也不保证适用于其他面板。

## 没有包含的第三方材料

- 厂商 datasheet PDF、第三方仓库整包副本、参考源码摘录：版权和体积原因未放入本包，研究时的参考副本留在原实验仓库，未随本仓库分发。
- 相机照片、视频、实验日志：属于原始证据，未放入本包。

## 免责声明

本包是逆向研究资料，不是厂商发布的生产驱动。按本文操作可能导致面板损坏、画面异常或数据丢失；请自行承担风险。尤其是：

- 不要写 MTP/OTP；
- 不要超过已验证的电压/时序范围；
- 不要在没有 POF/复位保护的情况下长时间跑实验。
