"""Dependency-free fixture preparation and container-output validation for CI."""

from __future__ import annotations

import csv
import struct
import sys
import zlib
from pathlib import Path


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    contents = chunk_type + payload
    return (
        struct.pack(">I", len(payload))
        + contents
        + struct.pack(">I", zlib.crc32(contents) & 0xFFFFFFFF)
    )


def make_png(path: Path) -> None:
    width = height = 8
    rows = []
    for y_position in range(height):
        row = bytearray([0])
        for x_position in range(width):
            row.extend(
                (
                    x_position * 31,
                    y_position * 31,
                    (x_position + y_position) * 15,
                )
            )
        rows.append(bytes(row))
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    )
    png += _png_chunk(b"IDAT", zlib.compress(b"".join(rows)))
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def prepare(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    make_png(directory / "smoke.png")


def validate(path: Path) -> None:
    with path.open(newline="", encoding="utf-8") as input_file:
        reader = csv.DictReader(input_file)
        assert reader.fieldnames == ["filename", "group_id"]
        assert list(reader) == [{"filename": "smoke.png", "group_id": "0"}]


def main() -> int:
    if len(sys.argv) != 3 or sys.argv[1] not in {"prepare", "validate"}:
        raise SystemExit(f"usage: {sys.argv[0]} prepare|validate PATH")
    path = Path(sys.argv[2])
    if sys.argv[1] == "prepare":
        prepare(path)
    else:
        validate(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
