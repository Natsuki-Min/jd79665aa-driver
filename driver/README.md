# driver · Pico 最小驱动

默认示例程序的流程是：复位、初始化、画一张 800×600 四色图、全刷、关电。

## 构建

以下命令在 `driver/` 目录执行。依赖 CMake、Ninja、Arm GNU Toolchain、Pico SDK（含 TinyUSB 子模块）和 picotool。已验证环境见 [软件验证记录](../docs/07-validation.md)。

```sh
./build.sh
```

默认使用 `~/.pico-sdk/`。其他机器：

```sh
./build.sh \
  -DPICO_SDK_PATH=/path/to/pico-sdk \
  -DPICO_TOOLCHAIN_PATH=/path/to/arm-toolchain \
  -Dpicotool_DIR=/path/to/picotool-cmake-package
```

`picotool_DIR` 指向包含 `picotoolConfig.cmake` 的目录。输出 `build/epd_bringup.uf2`。按住 BOOTSEL，复制到 `RPI-RP2`。

## 串口

miniterm 需要另装 `pyserial`；也可以使用 `screen`。离线工具不需要这项依赖。

```sh
python3 -m serial.tools.miniterm /dev/ttyACM0 115200
# 或 screen /dev/ttyACM0 115200
```

- `r`：重画测试图
- `s`：打印状态

## 文件

| 文件 | 内容 |
| --- | --- |
| `src/epd.h` | 引脚、几何、颜色码、API |
| `src/epd.c` | SPI、复位、初始化表、全窗、DTM、DRF、POF |
| `src/main.c` | 四色测试图 + 串口控制台 |
| `CMakeLists.txt` | 单目标 `epd_bringup` |

## API

```c
void epd_spi_init(void);
bool epd_init(void);                 // 复位 + 初始化寄存器
bool epd_power_on(void);             // 0x04
bool epd_write_frame(const uint8_t *frame, size_t length);  // 120000 B
bool epd_refresh(void);              // 全窗 + 0x12
bool epd_partial_update(uint16_t x, uint16_t y, uint16_t w, uint16_t h,
                        const uint8_t *data, size_t length);
bool epd_power_off(void);            // 0x02
```

`epd_partial_update()` 的 `x/y` 是**可见坐标**，`w` 是 4 的倍数，数据紧排 `w*h/4` 字节。它仍然使用原厂全刷波形，所以还是约 15 秒；它只解决窗口映射，不解决速度。

这些 API 需要先调用 `epd_spi_init()`。调用窗口更新前需完成 `epd_init()` 和 `epd_power_on()`，结束时调用 `epd_power_off()`。错误恢复由调用方负责；示例程序在任一步失败后会尽力 POF，再复位。

## 边界

- 不写 MTP/OTP。
- 不实现 R93/R92 回读。
- 不实现自定义 R20 波形；它需要同时改 PSR/R01/PLL 和一张完整表，属于实验路径，见 `docs/04-lut.md`。
- 初始化字节是实板验证值，不要按公开 datasheet 改。

完整说明：[初始化与全刷](../docs/02-init-and-refresh.md)、[R83 窗口](../docs/03-image-and-window.md)、[R20 波形](../docs/04-lut.md)。
