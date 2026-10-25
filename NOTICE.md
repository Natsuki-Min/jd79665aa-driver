# 来源、署名与许可

## 驱动代码

`driver/src/epd.c` 的初始化/全刷序列移植自：

- [krstc/openepaperlinkforCN · jd79665.cpp](https://github.com/krstc/openepaperlinkforCN/blob/42bd21471b5d3a6df07fd5ff9639fb88b5bcdc11/tag_fw/src/epd_driver/jd79665.cpp)，commit `42bd21471b5d3a6df07fd5ff9639fb88b5bcdc11` 的 `epdSetup()`、`epdWriteDisplayDataPhysicalFrame()`、`drawNoWait()`、`powerOff()`；
- 并和 [EPD_3in98g.cpp](https://github.com/krstc/openepaperlinkforCN/blob/42bd21471b5d3a6df07fd5ff9639fb88b5bcdc11/refdoc/BLE_EPD_DISPLAY/EPD_3in98g.cpp)、[panyihang/3.98Inch-ESP32C3-EPD · epd_panel.c](https://github.com/panyihang/3.98Inch-ESP32C3-EPD/blob/779eab27ba8b914e097fec530d1e1d601265fdcc/main/epd_panel.c)（commit `779eab27ba8b914e097fec530d1e1d601265fdcc`）交叉核对过。

移植文件头保留了来源项目、提交号和函数名。整理时，本地保存的 `openepaperlinkforCN` 参考版本未发现仓库级 LICENSE，`jd79665.cpp` 本身也未声明许可证；另一份 ESP32-C3 参考文件标注 `Unlicense OR CC0-1.0`，这不代表它能替前者授权。这里记录来源文件的许可状态，未为上游重新声明许可证。

`driver/pico_sdk_import.cmake` 是 Raspberry Pi Pico SDK 的 BSD-3-Clause 副本，文件内保留了版权和许可全文。

## 文档、解码结果与数据

`docs/`、`host/`、`data/` 里的整理文字、解码器、状态表和 `mtp.bin` 来自本项目的实验工作。除第三方代码外，本仓库**暂未声明统一的开源许可证**。

`data/mtp.bin` 是从这一块 SE0398NZ07A1 面板读出的 4096 B MTP 内容。样本保留工厂数据/标识（例如 `CJ1TM`、`NK863`），用于复现容器解码；其完整用途及与运行时波形配置的关系见 [MTP 说明](docs/05-mtp.md)。

## 没有包含的第三方材料

- 厂商 datasheet PDF、第三方仓库整包副本、参考源码摘录：版权和体积原因未放入本包，研究时的参考副本留在原实验仓库，未随本仓库分发。
- 相机照片、视频、实验日志：属于原始证据，未放入本包。
