#!/usr/bin/env python3
"""Print a 535-byte LUT table as human-readable states.

Examples:
    python3 show_profile.py                       # data/profile-01.logical.bin
    python3 show_profile.py --lane 5
    python3 show_profile.py data/profile-01.r20.wire.bin --wire
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from lut_codec import decode_byte, unpack_logical_state

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
TABLE_BYTES = 535


def parse_table(data: bytes, wire: bool = False) -> dict:
    if len(data) != TABLE_BYTES:
        raise ValueError("table must be 535 bytes, got %d" % len(data))
    logical = bytes(decode_byte(value) for value in data) if wire else data
    lanes = []
    for lane in range(6):
        states = []
        for state in range(8):
            start = 7 + lane * 88 + state * 11
            values = list(logical[start:start + 11])
            parsed = unpack_logical_state(values)
            states.append({
                "state": state,
                "G": values[0],
                "ABC": values[1],
                "DEF": values[2],
                "A": values[3],
                "B": values[4],
                "C": values[5],
                "RA": values[6],
                "D": values[7],
                "E": values[8],
                "F": values[9],
                "RB": values[10],
                "scans": parsed["scheduled_scans"],
            })
        lanes.append({"lane": lane, "states": states,
                      "total": sum(item["scans"] for item in states)})
    return {
        "header_hex": logical[:7].hex(" ").upper(),
        "lanes": lanes,
        "lane_totals": [lane["total"] for lane in lanes],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=DATA / "profile-01.logical.bin")
    parser.add_argument("--wire", action="store_true",
                        help="input is R20 wire order (default: logical)")
    parser.add_argument("--lane", type=int, choices=range(6))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    wire = args.wire or "wire" in args.path.name
    table = parse_table(args.path.read_bytes(), wire=wire)
    if args.lane is not None:
        table["lanes"] = [lane for lane in table["lanes"]
                          if lane["lane"] == args.lane]
        table["lane_totals"] = [table["lane_totals"][args.lane]]
    if args.json:
        print(json.dumps(table, indent=2, ensure_ascii=False))
        return 0

    print("file   : %s" % args.path)
    print("order  : %s" % ("R20 wire" if wire else "logical"))
    print("header : %s" % table["header_hex"])
    print("totals : " + ", ".join("H%d=%d" % (lane["lane"], lane["total"])
                                   for lane in table["lanes"]))
    print()
    print("lane state   G  ABC  DEF   A   B   C  RA   D   E   F  RB  scans")
    for lane in table["lanes"]:
        for item in lane["states"]:
            print("H%-2d  %-5d %3d  %3d  %3d %3d %3d %3d %3d %3d %3d %3d %3d %6d"
                  % (lane["lane"], item["state"], item["G"], item["ABC"],
                     item["DEF"], item["A"], item["B"], item["C"], item["RA"],
                     item["D"], item["E"], item["F"], item["RB"],
                     item["scans"]))
        print("     total %d scans" % lane["total"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
