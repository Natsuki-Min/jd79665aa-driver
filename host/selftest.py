#!/usr/bin/env python3
"""Offline self-test for the shared LUT/MTP tools.

Run: python3 selftest.py
No hardware, no external Python packages.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import decode_mtp  # noqa: E402
import lut_codec  # noqa: E402
import mtp_lz  # noqa: E402


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def synthetic_dump() -> bytes:
    """Two empty profiles with a different header, using overlapping LZ copies."""
    tokens = [mtp_lz.Token("literal", 0, 0, 0, 0, literal=lut_codec.encode_byte(1)),
              mtp_lz.Token("literal", 0, 0, 0, 0, literal=lut_codec.encode_byte(0))]
    remaining = 2 * decode_mtp.TABLE_BYTES - 2
    while remaining:
        length = min(257, remaining)
        assert length >= 3
        tokens.append(mtp_lz.Token("reference", 0, 0, 0, 0,
                                  length_code=length - 3, distance=1))
        remaining -= length
    tokens.append(mtp_lz.Token("end", 0, 0, 0, 0, length_code=255, distance=0))
    raw = bytearray(4096)
    start = mtp_lz.MTP_STREAM_START_BYTE * 8
    for i, bit in enumerate(mtp_lz.token_bits(tokens), start):
        raw[i // 8] |= bit << (i % 8)
    return bytes(raw)


def main() -> int:
    # 1. Byte codec is a bijection and matches the measured table.
    for value in range(256):
        assert lut_codec.decode_byte(lut_codec.encode_byte(value)) == value
    known = {0x00: 0xFF, 0x01: 0xEF, 0x02: 0x7F, 0x04: 0xBF, 0x08: 0xFD,
             0x10: 0xFE, 0x20: 0xF7, 0x40: 0xFB, 0x80: 0xDF}
    for logical, wire in known.items():
        assert lut_codec.encode_byte(logical) == wire

    # 2. One state round-trips and the scan formula is the known 108.
    state = lut_codec.pack_state(3, [0, 1, 2, 0, 1, 2],
                                 [2, 3, 4, 1, 2, 3], [2, 3])
    parsed = lut_codec.unpack_state(state)
    assert parsed["scheduled_scans"] == 108
    assert parsed["logical"] == [3, 0x18, 0x18, 2, 3, 4, 2, 1, 2, 3, 3]

    # 3. Decode the real dump and check the two table blocks.
    raw = (HERE.parent / "data" / "mtp.bin").read_bytes()
    assert sha256(raw) == decode_mtp.KNOWN_SHA256
    result = decode_mtp.decode_dump(raw)
    assert [p["header_hex"] for p in result["profiles"]] == list(decode_mtp.KNOWN_HEADERS)
    assert [p["lane_scan_totals"] for p in result["profiles"]] == [
        [1399] * 6, [742] * 6]
    assert len(result["decoded"].tokens) == 374 + 159 + 1

    # 4. The checked-in profile files are exactly what the decoder produces.
    for profile in result["profiles"]:
        stem = "profile-%02d" % profile["index"]
        logical = (HERE.parent / "data" / (stem + ".logical.bin")).read_bytes()
        wire = (HERE.parent / "data" / (stem + ".r20.wire.bin")).read_bytes()
        assert logical == profile["logical"], stem
        assert wire == profile["wire"], stem
        assert sha256(logical) == profile["sha256_logical"], stem
        assert sha256(wire) == profile["sha256_wire"], stem

    # 5. Wire bytes must decode back to logical bytes.
    for profile in result["profiles"]:
        assert bytes(map(lut_codec.decode_byte, profile["wire"])) == profile["logical"]

    # 6. Verify the manifest independently, including the raw dump.
    data_dir = HERE.parent / "data"
    entries = (data_dir / "SHA256SUMS").read_text().splitlines()
    assert len(entries) == 5
    for line in entries:
        digest, name = line.split()
        assert sha256((data_dir / name).read_bytes()) == digest, name

    # 7. Exercise a different, synthetic header and timing through the real CLI.
    # This must be refused by default, but parse with --allow-unknown without
    # claiming the reference dump's header/timing checks passed.
    unknown = synthetic_dump()
    alternate = decode_mtp.decode_dump(unknown)
    assert alternate["profiles"][0]["header_hex"] == "01 00 00 00 00 00 00"
    assert alternate["profiles"][0]["lane_scan_totals"] == [0] * 6
    assert len(alternate["logical"]) == 1070
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "synthetic.bin"
        source.write_bytes(unknown)
        command = [sys.executable, str(HERE / "decode_mtp.py"), "--source", str(source)]
        refused = subprocess.run(command, capture_output=True, text=True)
        assert refused.returncode != 0 and "unknown dump SHA256" in refused.stderr
        accepted = subprocess.run(command + ["--allow-unknown", "--json"],
                                  capture_output=True, text=True, check=True)
        report = json.loads(accepted.stdout)
        assert report["known_dump"] is False
        assert report["profiles"][0]["header_hex"] == "01 00 00 00 00 00 00"
        assert report["profiles"][0]["lane_scan_totals"] == [0] * 6
        assert report["logical_tail"]["all_zero_from"] == 1070

    # 8. Reject truncated tokens, invalid references and excessive output.
    for data, options in ((b"\x00", {"start_bit": 0}),
                          (b"\x01\x02\x00", {"start_bit": 0}),
                          (unknown, {"max_output": 100})):
        try:
            mtp_lz.decode(data, **options)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid or oversized stream was accepted")

    print("selftest: OK")
    print("  dump      : 4096 B, %s" % decode_mtp.KNOWN_SHA256)
    print("  LZ output : %d B, %d tokens" % (len(result["logical"]),
                                               len(result["decoded"].tokens)))
    print("  profile 0 : %s, 1399 scans/lane" % result["profiles"][0]["header_hex"])
    print("  profile 1 : %s, 742 scans/lane" % result["profiles"][1]["header_hex"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
