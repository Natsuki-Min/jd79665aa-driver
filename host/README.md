# host · 波形与 MTP 的离线工具

这组工具把文件中的字节变成可读的时序字段，也能把逻辑状态编码成 R20 wire 字节。需要 Python 3.9 或更新版本，仅使用标准库。以下命令在 `host/` 目录执行。

## 从样本看到状态

```sh
python3 selftest.py
python3 decode_mtp.py
python3 show_profile.py --lane 5
```

`decode_mtp.py` 完成 LZ 解压、R20 逆映射和两张表的提取。`show_profile.py` 将一张表按路径和状态打印，能看到 G、相位扫描数、RA/RB 以及计划总扫描数。H5 控制已观察到的供电模式，因此常用于和 VSL 跳变时刻比较。

`selftest.py` 检查字节双射、108 扫描状态、真实样本、文件哈希，以及解出的 profile 1 与独立硬件测量掩码的匹配。详见 [复现说明](../docs/07-validation.md)。

## 解码与导出

```sh
python3 decode_mtp.py --json
python3 decode_mtp.py --out /tmp/jd79665-decoded
```

导出包括完整的 `decoded-stream.logical.bin`、`decoded-stream.wire.bin`，以及两张 profile 的 logical/wire 文件。默认源文件为 `../data/mtp.bin`，工具检查该样本的 SHA256、头部、六路扫描总数和 token 重新序列化结果。

研究另一份相同布局的 dump 时，可指定：

```sh
python3 decode_mtp.py --source /path/to/another-mtp.bin --allow-unknown --json
```

`--allow-unknown` 跳过参考样本特有的哈希、头部与扫描数，保留解析器的结构检查。当前结构假设是 4096 B 容器、固定流起点 `0x016`、两张连续的 535 B 表，且每张表六路扫描数相等。尾部边界由实际输出计算。因此这个选项适合比较同布局样本；扩展到不同容器时可从 `mtp_lz.decode()` 单独调用底层解码器。

## 查看任意一张表

```sh
python3 show_profile.py
python3 show_profile.py --lane 5
python3 show_profile.py ../data/profile-00.logical.bin
python3 show_profile.py ../data/profile-01.r20.wire.bin --wire
python3 show_profile.py --json --lane 5
```

输入 logical 文件时直接解析字段；wire 文件先做 R20 逆映射。文件名包含 `wire` 时会自动选择该转换。

## 生成一个状态

```python
from lut_codec import pack_state, unpack_state

wire = pack_state(3, [0,1,2,0,1,2], [2,3,4,1,2,3], [2,3])
assert unpack_state(wire)["scheduled_scans"] == 108
```

参数依次是 G、A–F 电平码、A–F 扫描数、RA/RB。返回的 11 B 已是 wire 字节，可放入所需路径的状态位置。表头、其他路径、图像类别和供电配置由调用方组织；这些关系见 [R20 章节](../docs/04-lut.md)。

## 模块分工

| 模块 | 可复用内容 |
| --- | --- |
| `lut_codec.py` | 单字节映射、逻辑/wire 状态打包解析、表块拼装 |
| `mtp_lz.py` | LSB-first token 解码、重叠回溯、token 重新序列化 |
| `decode_mtp.py` | 本样本容器布局、表块提取、摘要与导出 |
| `show_profile.py` | 535 B 表块的字段化显示 |
| `selftest.py` | 样本、格式与独立字段参照的检查入口 |
