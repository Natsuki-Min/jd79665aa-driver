# 07 · 软件验证与复现

软件验证日期：**2026-10-25**。以下命令检查随仓库提供的格式、样本和驱动构建；硬件实验的对照方法与结果见 [快刷实验](06-refresh-experiments.md)。

所有命令均从本仓库根目录执行。

## 1. 离线工具

```sh
python3 host/selftest.py
python3 host/lut_codec.py
python3 host/mtp_lz.py
python3 host/decode_mtp.py
python3 host/show_profile.py --lane 5
(cd data && sha256sum -c SHA256SUMS)
```

自检覆盖：

- 全部 256 个字节的编解码往返与已知单 bit 映射；
- 11 B 状态的打包、字段解析和 108 扫描示例；
- 真实 MTP 样本的哈希、LZ token 重新序列化、两张表及扫描总数；
- 仓库内四个表文件与解码输出逐字节一致，以及六个参考文件的 SHA256SUMS；
- profile 1 与独立测量参照的 3194 个已辨识位、66 个候选位，以及 432 个时长字节的对照；
- 合成的不同头部/扫描数样本：默认拒绝，`--allow-unknown` 可按相同布局解码，摘要中标记为未知样本；
- LZ 重叠复制、截断输入、越界引用和输出上限。

参考样本应得到：

| 项目 | 结果 |
| --- | --- |
| MTP | 4096 B，SHA256 `150470090f544d6f8da303ce0fbe8f085c129e7b325e44bca9157a191dcddda4` |
| LZ | 7046 bit，374 literal + 159 reference + 1 end |
| 解压输出 | 11510 B |
| profile 0 | 535 B，头部 `00 3C 28 78 3E 00 08`，六轨各 1399 扫描 |
| profile 1 | 535 B，头部 `00 22 24 78 22 00 08`，六轨各 742 扫描 |

也可以重新导出到临时目录，与仓库样本比较：

```sh
python3 host/decode_mtp.py --out /tmp/jd79665-decoded
cmp data/profile-00.logical.bin /tmp/jd79665-decoded/profile-00.logical.bin
cmp data/profile-00.r20.wire.bin /tmp/jd79665-decoded/profile-00.r20.wire.bin
cmp data/profile-01.logical.bin /tmp/jd79665-decoded/profile-01.logical.bin
cmp data/profile-01.r20.wire.bin /tmp/jd79665-decoded/profile-01.r20.wire.bin
```

`cmp` 成功时不输出文字。`data/measured-reference.json` 提供独立测量代表值与位掩码，`selftest.py` 可复现其与解码表的比较；测量方法及掩码含义见 [MTP 实测对照](05-mtp.md#4-profile-1-和实测对上了什么)。

## 2. 固件构建

已在以下环境运行 `./driver/build.sh` 并生成 `epd_bringup.elf` 和 `epd_bringup.uf2`：

| 项目 | 版本 / 设置 |
| --- | --- |
| 目标板 | Raspberry Pi Pico / RP2040 |
| Pico SDK | 2.3.1 |
| Arm GNU Toolchain | 15.2.Rel1（GCC 15.2.1） |
| picotool | 2.3.1 |
| 构建类型 | Release，C11 |
| 编译警告 | `-Wall -Wextra -Werror` |

这些版本记录了当前可构建环境，便于遇到工具链差异时对照。此次运行了软件构建与离线检查；整理后的程序尚未重新进行显示及错误恢复的实板测试。

## 3. 仍需硬件验证的部分

- 整理后的最小驱动在目标板上的显示效果和错误恢复路径；
- 解出的两张 535 B 表块在 R20 空间中的完整加载及 BUSY/VSL/光学对照；
- 不同面板批次、温度档、供电与长期运行行为。

来源见 [NOTICE.md](../NOTICE.md)，完整实验思路见 [快刷实验](06-refresh-experiments.md)。
