#!/usr/bin/env python3
"""Decode data/mtp.bin and extract the two 535-byte waveform tables.

Usage:
    python3 decode_mtp.py                 # verify + print summary
    python3 decode_mtp.py --json          # machine-readable summary
    python3 decode_mtp.py --out /tmp/mtp  # write decoded bytes and profiles

This is an offline tool. It does not open a serial port or touch the panel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from lut_codec import decode_byte
from mtp_lz import decode, state_scans, token_bits

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
TABLE_BYTES = 7 + 6 * 8 * 11  # 535
KNOWN_SHA256 = "150470090f544d6f8da303ce0fbe8f085c129e7b325e44bca9157a191dcddda4"
KNOWN_HEADERS = ("00 3C 28 78 3E 00 08", "00 22 24 78 22 00 08")
KNOWN_TOTALS = (1399, 742)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_profile(logical: bytes, wire: bytes, offset: int, index: int) -> dict:
    block = logical[offset:offset + TABLE_BYTES]
    wire_block = wire[offset:offset + TABLE_BYTES]
    if len(block) != TABLE_BYTES:
        raise ValueError("profile %d is truncated" % index)
    states = []
    lane_totals = []
    for lane in range(6):
        total = 0
        for state in range(8):
            start = 7 + lane * 88 + state * 11
            values = list(block[start:start + 11])
            scans = state_scans(values)
            total += scans
            states.append({
                "lane": lane,
                "state": state,
                "G": values[0],
                "ABC_levels": values[1],
                "DEF_levels": values[2],
                "A": values[3],
                "B": values[4],
                "C": values[5],
                "RA": values[6],
                "D": values[7],
                "E": values[8],
                "F": values[9],
                "RB": values[10],
                "scheduled_scans": scans,
            })
        lane_totals.append(total)
    if len(set(lane_totals)) != 1:
        raise ValueError("profile %d lanes disagree: %s" % (index, lane_totals))
    return {
        "index": index,
        "offset": offset,
        "header": block[:7],
        "header_hex": block[:7].hex(" ").upper(),
        "logical": block,
        "wire": wire_block,
        "sha256_logical": sha256(block),
        "sha256_wire": sha256(wire_block),
        "lane_scan_totals": lane_totals,
        "states": states,
    }


def decode_dump(raw: bytes) -> dict:
    if len(raw) != 4096:
        raise ValueError("expected a 4096-byte MTP dump, got %d" % len(raw))
    decoded = decode(raw, end_bit=0xF00 * 8)
    logical = decoded.logical
    if token_bits(decoded.tokens) != [
            (raw[i // 8] >> (i % 8)) & 1
            for i in range(decoded.start_bit, decoded.end_bit)]:
        raise ValueError("token re-serialization does not match the stream")
    profiles = [extract_profile(logical, decoded.wire, 0, 0),
                extract_profile(logical, decoded.wire, 535, 1)]
    return {"decoded": decoded, "logical": logical, "profiles": profiles}


def summary(result: dict, source: Path, digest: str) -> dict:
    decoded = result["decoded"]
    profiles = result["profiles"]
    tail_start = 2 * TABLE_BYTES
    last_nonzero = next((i for i in range(len(result["logical"]) - 1, tail_start - 1, -1)
                         if result["logical"][i]), None)
    return {
        "source": str(source),
        "source_bytes": 4096,
        "source_sha256": digest,
        "known_dump": digest == KNOWN_SHA256,
        "stream": {
            "start_byte": decoded.start_bit // 8,
            "end_byte": decoded.end_bit // 8,
            "end_bit_in_byte": decoded.end_bit % 8,
            "token_bits": len(token_bits(decoded.tokens)),
            "output_bytes": len(decoded.wire),
            "tokens": {
                "literal": sum(t.kind == "literal" for t in decoded.tokens),
                "reference": sum(t.kind == "reference" for t in decoded.tokens),
                "end": sum(t.kind == "end" for t in decoded.tokens),
            },
        },
        "profiles": [{
            "index": profile["index"],
            "offset": profile["offset"],
            "bytes": TABLE_BYTES,
            "header_hex": profile["header_hex"],
            "lane_scan_totals": profile["lane_scan_totals"],
            "sha256_logical": profile["sha256_logical"],
            "sha256_wire": profile["sha256_wire"],
        } for profile in profiles],
        "logical_tail": {
            "profile0_end": 535,
            "profile1_end": 1070,
            "opaque_nonzero_end": last_nonzero,
            "all_zero_from": tail_start if last_nonzero is None else last_nonzero + 1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DATA / "mtp.bin")
    parser.add_argument("--out", type=Path, help="write decoded stream/profiles here")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-unknown", action="store_true",
                        help="do not fail if the dump hash is not the known one")
    args = parser.parse_args()

    raw = args.source.read_bytes()
    digest = sha256(raw)
    if digest != KNOWN_SHA256 and not args.allow_unknown:
        raise SystemExit("unknown dump SHA256: %s\n"
                         "(pass --allow-unknown to decode anyway)" % digest)
    result = decode_dump(raw)
    report = summary(result, args.source, digest)

    # Reference headers and timings belong to this dump, not every panel.
    if report["known_dump"]:
        for profile, header, total in zip(result["profiles"], KNOWN_HEADERS, KNOWN_TOTALS):
            if profile["header_hex"] != header:
                raise SystemExit("unexpected header for profile %d: %s"
                                 % (profile["index"], profile["header_hex"]))
            if profile["lane_scan_totals"] != [total] * 6:
                raise SystemExit("unexpected lane totals for profile %d: %s"
                                 % (profile["index"], profile["lane_scan_totals"]))
    # The wire profile must decode back to the logical profile.
    for profile in result["profiles"]:
        if bytes(decode_byte(value) for value in profile["wire"]) != profile["logical"]:
            raise SystemExit("wire/logical mismatch in profile %d" % profile["index"])

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "decoded-stream.logical.bin").write_bytes(result["logical"])
        (args.out / "decoded-stream.wire.bin").write_bytes(result["decoded"].wire)
        for profile in result["profiles"]:
            stem = "profile-%02d" % profile["index"]
            (args.out / (stem + ".logical.bin")).write_bytes(profile["logical"])
            (args.out / (stem + ".r20.wire.bin")).write_bytes(profile["wire"])

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    stream = report["stream"]
    print("MTP dump : %s (%d B)" % (args.source, report["source_bytes"]))
    print("SHA256   : %s" % report["source_sha256"])
    print("LZ stream: starts 0x%03X, ends 0x%03X bit %d, %d bits"
          % (stream["start_byte"], stream["end_byte"],
             stream["end_bit_in_byte"], stream["token_bits"]))
    print("Tokens   : %(literal)d literal, %(reference)d reference, %(end)d end"
          % stream["tokens"])
    print("Output   : %d bytes (R20 wire order)" % stream["output_bytes"])
    for profile in report["profiles"]:
        print("Profile %d: offset %d, header %s, %d scans x 6 lanes"
              % (profile["index"], profile["offset"], profile["header_hex"],
                 profile["lane_scan_totals"][0]))
        print("           logical %s" % profile["sha256_logical"])
        print("           wire    %s" % profile["sha256_wire"])
    tail = report["logical_tail"]
    print("Tail     : opaque data starts at 1070; all zero from %d"
          % tail["all_zero_from"])
    if report["known_dump"]:
        print("OK: known dump, headers, lane totals and byte mapping verified")
    else:
        print("OK: stream parsed under the assumed two-profile layout; byte mapping verified")
        print("UNKNOWN DUMP: reference headers/timings were not checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
