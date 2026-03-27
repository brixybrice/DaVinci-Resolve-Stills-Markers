#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HDR PNG tagger — inserts a cICP chunk into PNG files for HDR color space tagging.
Pure Python, no external binaries required (struct + zlib only).

CICP values follow ITU-T H.273 / ISO 23091-2.
"""

import struct
import zlib

# ── Color space constants ─────────────────────────────────────────────────────
BT_1886        = "None (sRGB)"
DCI_P3         = "SDR DCI-P3"
BT_2100_PQ     = "HDR BT.2100 PQ"
BT_2100_HLG    = "HDR BT.2100 HLG"
BT_2100_PQ_P3  = "HDR BT.2100 PQ (P3 limited)"
BT_2100_HLG_P3 = "HDR BT.2100 HLG (P3 limited)"

COLOR_TAGS = [BT_1886, DCI_P3, BT_2100_PQ, BT_2100_HLG, BT_2100_PQ_P3, BT_2100_HLG_P3]

# ── CICP mapping ──────────────────────────────────────────────────────────────
# [Color Primaries, Transfer Function, Matrix Coefficients, Video Full Range]
_CICP_MAP = {
    BT_1886:        [1,  1,  0, 0],   # BT.709 / sRGB
    DCI_P3:         [11, 8,  9, 0],   # DCI-P3, Linear
    BT_2100_PQ:     [9,  16, 9, 0],   # BT.2100, PQ
    BT_2100_HLG:    [9,  18, 9, 0],   # BT.2100, HLG
    BT_2100_PQ_P3:  [11, 16, 9, 0],   # DCI-P3 primaries, PQ
    BT_2100_HLG_P3: [11, 18, 9, 0],   # DCI-P3 primaries, HLG
}


def tag_png_with_cicp(png_path: str, colortag: str) -> None:
    """
    Insert a cICP chunk into a PNG file (in-place).

    The cICP chunk is placed immediately after the IHDR chunk (offset 0x21),
    as required by the PNG spec for color space metadata.
    No-op for BT_1886 (sRGB) since it is the PNG default.
    """
    if colortag == BT_1886:
        return

    cicp = _CICP_MAP.get(colortag)
    if cicp is None:
        raise ValueError(f"Unknown color tag: {colortag!r}")

    chunk_type = b"cICP"
    data       = struct.pack(">4B", *cicp)
    length     = struct.pack(">I", len(data))
    crc        = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
    cicp_chunk = length + chunk_type + data + crc

    with open(png_path, "rb") as f:
        original = f.read()

    # Offset 0x21 = 8 (PNG signature) + 25 (IHDR chunk: 4 length + 4 type + 13 data + 4 CRC)
    offset = 0x21
    if len(original) <= offset:
        raise ValueError(f"File too small to be a valid PNG: {png_path}")

    with open(png_path, "wb") as f:
        f.write(original[:offset] + cicp_chunk + original[offset:])


def process_still(png_path: str, colortag: str) -> None:
    """
    Tag a PNG still with HDR color space information (in-place).
    No-op if colortag is BT_1886 (sRGB default).
    Raises ValueError for unknown color tags or invalid PNG.
    """
    tag_png_with_cicp(png_path, colortag)
