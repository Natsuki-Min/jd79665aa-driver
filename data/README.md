# 数据文件

这里的文件都很小，全部来自同一块 SE0398NZ07A1 面板，用于离线复现。

| 文件 | 大小 | 内容 |
| --- | ---: | --- |
| `mtp.bin` | 4096 B | 用 R92 读出的原始 MTP 内容，未改动 |
| `profile-00.logical.bin` | 535 B | 解出的第一张状态表（逻辑字节序），六轨各 1399 扫描 |
| `profile-00.r20.wire.bin` | 535 B | 同上，但已转成 R20 线上字节序 |
| `profile-01.logical.bin` | 535 B | 解出的第二张状态表（逻辑字节序），六轨各 742 扫描 |
| `profile-01.r20.wire.bin` | 535 B | 同上，但已转成 R20 线上字节序 |

SHA256：

```text
150470090f544d6f8da303ce0fbe8f085c129e7b325e44bca9157a191dcddda4  mtp.bin
8a3fd8834a012ad2101dab7f9ee84965f6384262380df2f9e0d319fdb6b3f28a  profile-00.logical.bin
a0e029f54f2e33e895752d30005f1b3b673e1485703b387959e2b382c05f431a  profile-00.r20.wire.bin
c33e309ac9bc30d05dbe9c7e5aa1fb33371e3055922281c48adab1844da2429c  profile-01.logical.bin
3ef7af3231d8f81b4e64a871cd9405e30dea000a541f45dcc6fb8f696513f899  profile-01.r20.wire.bin
```

## 怎么理解这些表

- 一张表 = 7 字节头 + 6 条轨 × 8 个状态 × 11 字节 = **535 字节**。
- `profile-01` 与历史 BUSY/VSL 实测表的已辨识位一致；代表字节中有一处未执行子组的等价差异，见 [详细对照](../docs/05-mtp.md#profile-1-和实测对上了什么)。
- `profile-00` 是同一个压缩流里的另一张表，六轨各 1399 扫描。它可能是另一个温度档，但**选表规则尚未验证**。
- `.logical.bin` 是解读用的逻辑字节；`.r20.wire.bin` 是真正通过 SPI 写给 R20 的字节。两者不能混用。
- 535 字节只是识别出来的表块，不是完整的 2048 字节 R20 空间，也不是可以直接烧写的固件。

## 边界

- `mtp.bin` 来自**这一块**面板。其他批次、其他温度档可能不同，不要当作通用固件。
- 解码是离线完成的，没有把整张表上传回面板做电压/光学复现；不能宣称“原厂波形已完整跑通”。
- 本包只读 MTP，不提供写 MTP/OTP 的代码。请不要自行尝试编程 MTP 或 OTP。

重新生成这些文件：

```sh
cd host
python3 decode_mtp.py --out ../data
```
