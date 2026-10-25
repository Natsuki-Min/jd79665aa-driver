# host · 离线 Python 工具

需要 Python 3.9 或更新版本，仅使用标准库，不接串口、不碰面板。以下命令在 `host/` 目录执行。

| 文件 | 作用 |
| --- | --- |
| `lut_codec.py` | 逻辑字节 ↔ R20 线上字节；11 B 状态打包/解析 |
| `mtp_lz.py` | MTP 里的 LSB-first LZ 解码器 |
| `decode_mtp.py` | 解 `../data/mtp.bin`，提取两张 535 B 表并校验 |
| `show_profile.py` | 把 535 B 表打印成逐状态表格 |
| `selftest.py` | 一键自检：字节双射、108 扫描状态、真实 dump、文件哈希 |

## 先跑自检

```sh
python3 selftest.py
```

期望：

```text
selftest: OK
  dump      : 4096 B, 150470...
  LZ output : 11510 B, 534 tokens
  profile 0 : 00 3C 28 78 3E 00 08, 1399 scans/lane
  profile 1 : 00 22 24 78 22 00 08, 742 scans/lane
```

## 解码 MTP

```sh
python3 decode_mtp.py
python3 decode_mtp.py --json
python3 decode_mtp.py --out /tmp/mtp
```

它会校验：

- dump 大小 4096 B；
- SHA256 是否等于已知值（换 dump 要加 `--allow-unknown`）；
- 已知样本的两张表头部、六轨扫描总数；
- wire → logical 能还原。

`--allow-unknown` 只跳过已知样本的哈希、头部和扫描数校验；仍假设 4096 B 容器、固定流起点和两张连续 535 B 表，并要求每张表的六轨扫描数相等。它是同布局样本的探索入口，不是通用格式识别器，也不证明新样本可用于硬件。未知样本的尾部边界由解码结果计算。

## 看表

```sh
python3 show_profile.py                    # profile 1，全部轨
python3 show_profile.py --lane 5           # 只看 H5
python3 show_profile.py ../data/profile-01.r20.wire.bin --wire
python3 show_profile.py --json --lane 5
```

## 作为模块用

```python
from lut_codec import pack_state, unpack_state, encode_byte, decode_byte

wire = pack_state(3, [0, 1, 2, 0, 1, 2],
                  [2, 3, 4, 1, 2, 3], [2, 3])
assert unpack_state(wire)["scheduled_scans"] == 108
```

`pack_state()` 返回的是**wire 字节**，可以直接拼到 2048 B 表里；`unpack_state()` 接收的也是 wire 字节。

## 注意

- 这些工具只解释数据，不生成“已验证的完整 LUT”。头部 7 字节、H1 首状态、电平低位仍有未知。
- `decode_mtp.py --out ../data` 会覆盖 `data/` 里的 profile 文件；正常情况下输出应该逐字节一致。
- 不要用 `mtp.bin` 反推“所有面板都一样”。它只来自这一块屏。
