#!/usr/bin/env python3
"""Decoder for the LZ stream stored inside this panel's 4096-byte MTP dump.

The stream starts at MTP offset 0x016. Bits and integers are LSB-first:
    0 + literal:8                  -> one output byte
    1 + length_code:8 + distance:14 -> copy length_code+3 bytes from
                                       distance bytes back (overlap allowed)
    length_code=255, distance=0     -> end of stream

The decoder output is in the empirical R20 **wire** byte order. Apply
decode_byte() (from lut_codec.py) afterwards to get logical state bytes.

The module operates on byte strings.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

WIRE_BITS = (4, 7, 6, 1, 0, 3, 2, 5)
MTP_STREAM_START_BYTE = 0x016


def logical_byte(wire: int) -> int:
    """R20 wire byte -> logical byte (same as lut_codec.decode_byte)."""
    return sum((((wire ^ 0xFF) >> wire_bit) & 1) << bit
               for bit, wire_bit in enumerate(WIRE_BITS))


def wire_byte(logical: int) -> int:
    """Logical byte -> R20 wire byte (same as lut_codec.encode_byte)."""
    return 0xFF ^ sum(((logical >> bit) & 1) << wire_bit
                      for bit, wire_bit in enumerate(WIRE_BITS))


@dataclass
class Token:
    kind: str
    input_start_bit: int
    input_end_bit: int
    output_start: int
    output_end: int
    literal: Optional[int] = None
    length_code: Optional[int] = None
    distance: Optional[int] = None


@dataclass
class Decoded:
    wire: bytes
    start_bit: int
    end_bit: int
    tokens: list[Token]

    @property
    def logical(self) -> bytes:
        return bytes(logical_byte(value) for value in self.wire)

    def token_dicts(self) -> list[dict]:
        return [asdict(token) for token in self.tokens]


def decode(data: bytes, start_bit: int = MTP_STREAM_START_BYTE * 8,
           end_bit: Optional[int] = None, max_output: int = 65536) -> Decoded:
    """Decode to the explicit end token; reject truncation and bad references."""
    limit = len(data) * 8 if end_bit is None else end_bit
    if not 0 <= start_bit <= limit <= len(data) * 8:
        raise ValueError("invalid input bit bounds")
    at = start_bit
    out = bytearray()
    tokens: list[Token] = []

    def read(count: int) -> int:
        nonlocal at
        if at + count > limit:
            raise ValueError("truncated LZ token at bit %d" % at)
        value = sum(((data[(at + i) // 8] >> ((at + i) % 8)) & 1) << i
                    for i in range(count))
        at += count
        return value

    while True:
        begin = at
        dest = len(out)
        if read(1) == 0:
            value = read(8)
            if len(out) >= max_output:
                raise ValueError("decoded output limit exceeded")
            out.append(value)
            tokens.append(Token("literal", begin, at, dest, len(out), literal=value))
            continue
        length_code = read(8)
        distance = read(14)
        if distance == 0:
            if length_code != 255:
                raise ValueError("unsupported zero-distance token")
            tokens.append(Token("end", begin, at, dest, dest,
                                length_code=length_code, distance=0))
            return Decoded(bytes(out), start_bit, at, tokens)
        if length_code == 255:
            raise ValueError("unobserved length=255 / non-zero distance token")
        if distance > len(out):
            raise ValueError("reference distance %d before output start %d"
                             % (distance, len(out)))
        length = length_code + 3
        if len(out) + length > max_output:
            raise ValueError("decoded output limit exceeded")
        for _ in range(length):
            out.append(out[-distance])
        tokens.append(Token("reference", begin, at, dest, len(out),
                            length_code=length_code, distance=distance))


def token_bits(tokens: list[Token]) -> list[int]:
    """Re-serialize tokens for an integrity check (not a LUT compiler)."""
    result: list[int] = []

    def put(value: int, count: int) -> None:
        result.extend((value >> i) & 1 for i in range(count))

    for token in tokens:
        if token.kind == "literal":
            put(0, 1)
            put(token.literal, 8)
        else:
            put(1, 1)
            put(token.length_code, 8)
            put(token.distance, 14)
    return result


def phases(state: list[int]):
    """Yield (2-bit level code, scan count) for a non-empty state."""
    g, abc, def_levels, a, b, c, ra, d, e, f, rb = state
    for _ in range(g):
        for levels, counts, repeat in ((abc, [a, b, c & 0x7F], ra),
                                       (def_levels, [d, e, f & 0x7F], rb)):
            for _ in range(repeat):
                for shift, count in zip((6, 4, 2), counts):
                    if count:
                        yield (levels >> shift) & 3, count


def state_scans(state: list[int]) -> int:
    """Scheduled scan count under the empirical 11-byte model."""
    g, _abc, _def, a, b, c, ra, d, e, f, rb = state
    return g * ((a + b + (c & 0x7F)) * ra + (d + e + (f & 0x7F)) * rb)


def _self_test() -> None:
    for value in range(256):
        assert logical_byte(wire_byte(value)) == value
    # (literal 'A', end) in LSB-first bits: 0 + 0x41, then 255/0.
    bits = [0] + [(0x41 >> i) & 1 for i in range(8)] + [1] + \
           [(255 >> i) & 1 for i in range(8)] + [0] * 14
    data = bytes(sum(bits[i + j] << j for j in range(8))
                 for i in range(0, len(bits), 8))
    decoded = decode(data, start_bit=0, end_bit=len(bits))
    assert decoded.wire == b"A", decoded.wire
    print("mtp_lz self-test: OK")


if __name__ == "__main__":
    _self_test()
