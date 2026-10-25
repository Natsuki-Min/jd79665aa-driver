#!/usr/bin/env python3
"""R20 LUT byte codec and 11-byte state layout.

This module only handles the *digital* representation:
  logical state byte -> wire byte (what you send to R20).

It does not talk to hardware and does not know the factory MTP wrapper.

Wire encoding (verified on this panel):
    wire = 0xFF XOR permute(logical)
    logical bit 0..7 -> wire bit 4 7 6 1 0 3 2 5
"""
from __future__ import annotations

WIRE_BITS = (4, 7, 6, 1, 0, 3, 2, 5)
FIELD_NAMES = ("G", "ABC_levels", "DEF_levels", "A", "B", "C", "RA", "D", "E", "F", "RB")


def encode_byte(logical: int) -> int:
    """Logical byte -> R20 wire byte."""
    if not 0 <= logical <= 0xFF:
        raise ValueError("logical byte must be 0..255")
    return 0xFF ^ sum(((logical >> bit) & 1) << wire
                      for bit, wire in enumerate(WIRE_BITS))


def decode_byte(wire: int) -> int:
    """R20 wire byte -> logical byte."""
    if not 0 <= wire <= 0xFF:
        raise ValueError("wire byte must be 0..255")
    return sum((((wire ^ 0xFF) >> wire_bit) & 1) << bit
               for bit, wire_bit in enumerate(WIRE_BITS))


def pack_state(outer: int, levels: list[int] | tuple[int, ...],
               frames: list[int] | tuple[int, ...],
               repeats: list[int] | tuple[int, ...]) -> bytes:
    """Build one 11-byte state in **wire** order, ready to send to R20.

    outer   : G, outer repeat. 0 terminates this path.
    levels  : six 2-bit codes for A B C D E F (0..3).
    frames  : A B C D E F scan counts. C/F are limited to 0..127 because
              their bit 7 is not understood.
    repeats : RA (ABC sub-repeat), RB (DEF sub-repeat).
    """
    if len(levels) != 6 or len(frames) != 6 or len(repeats) != 2:
        raise ValueError("need six levels, six frames and two repeats")
    if not 0 <= outer <= 0xFF:
        raise ValueError("outer repeat must be 0..255")
    if any(not 0 <= value <= 3 for value in levels):
        raise ValueError("level codes must be 0..3")
    if not 0 <= repeats[0] <= 0xFF or not 0 <= repeats[1] <= 0xFF:
        raise ValueError("repeats must be 0..255")
    if any(not 0 <= frames[i] <= (127 if i in (2, 5) else 255)
           for i in range(6)):
        raise ValueError("A/B/D/E frames 0..255, C/F frames 0..127")
    a, b, c, d, e, f = frames
    abc_levels = sum(levels[i] << (6 - 2 * i) for i in range(3))
    def_levels = sum(levels[i + 3] << (6 - 2 * i) for i in range(3))
    logical = (outer, abc_levels, def_levels, a, b, c,
               repeats[0], d, e, f, repeats[1])
    return bytes(encode_byte(value) for value in logical)


def _parse_logical(logical: list[int]) -> dict:
    if len(logical) != 11:
        raise ValueError("one state is 11 logical bytes")
    levels = [(logical[1 + i // 3] >> (6 - 2 * (i % 3))) & 3 for i in range(6)]
    frames = [logical[3], logical[4], logical[5] & 0x7F,
              logical[7], logical[8], logical[9] & 0x7F]
    repeats = [logical[6], logical[10]]
    scans = logical[0] * (sum(frames[:3]) * repeats[0] +
                          sum(frames[3:]) * repeats[1])
    return {
        "logical": logical,
        "G": logical[0],
        "levels": levels,
        "frames": frames,
        "repeats": repeats,
        "scheduled_scans": scans,
        "c_f_high_bits": [logical[5] >> 7, logical[9] >> 7],
        "level_low_bits": [logical[1] & 3, logical[2] & 3],
    }


def unpack_state(word: bytes) -> dict:
    """Parse one 11-byte **wire** state into fields and scan count."""
    if len(word) != 11:
        raise ValueError("one state is 11 bytes")
    return _parse_logical([decode_byte(value) for value in word])


def unpack_logical_state(values: list[int] | tuple[int, ...]) -> dict:
    """Parse one already-decoded 11-value logical state."""
    return _parse_logical(list(values))


def pack_logical_state(values: list[int] | tuple[int, ...]) -> bytes:
    """Encode an already-decoded 11-value logical state."""
    if len(values) != 11:
        raise ValueError("one state is 11 logical bytes")
    return bytes(encode_byte(value) for value in values)


def build_table(header: bytes, lanes: list[list[bytes]]) -> bytes:
    """Build 535 wire bytes; header and all 6 x 8 states must be wire-encoded.

    Encode a logical header with bytes(map(encode_byte, logical_header)) first.
    This only assembles the block; it does not validate its hardware behavior.
    """
    if len(header) != 7:
        raise ValueError("header must be 7 bytes")
    if len(lanes) != 6 or any(len(lane) != 8 for lane in lanes):
        raise ValueError("expected six lanes of eight states")
    out = bytearray(header)
    for lane in lanes:
        for state in lane:
            if len(state) != 11:
                raise ValueError("each state must be 11 bytes")
            out += state
    if len(out) != 535:
        raise ValueError("table must be 535 bytes")
    return bytes(out)


def _self_test() -> None:
    for value in range(256):
        assert decode_byte(encode_byte(value)) == value
    known = {0x00: 0xFF, 0x01: 0xEF, 0x02: 0x7F, 0x04: 0xBF, 0x08: 0xFD,
             0x10: 0xFE, 0x20: 0xF7, 0x40: 0xFB, 0x80: 0xDF}
    for logical, wire in known.items():
        assert encode_byte(logical) == wire, (logical, encode_byte(logical))
    state = pack_state(3, [0, 1, 2, 0, 1, 2],
                       [2, 3, 4, 1, 2, 3], [2, 3])
    parsed = unpack_state(state)
    assert parsed["scheduled_scans"] == 108, parsed
    assert parsed["logical"] == [3, 0x18, 0x18, 2, 3, 4, 2, 1, 2, 3, 3]
    print("lut_codec self-test: OK (256 byte round-trips, known vectors, 108-scan state)")


if __name__ == "__main__":
    _self_test()
