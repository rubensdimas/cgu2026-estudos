"""Gera os ícones PNG do PWA (192 e 512 px) sem dependências externas.

Uso: python3 scripts/make_icons.py apps/web/public/icons
"""

import struct
import sys
import zlib
from pathlib import Path

BG = (0x0B, 0x12, 0x20)
XP = (0xFA, 0xCC, 0x15)
BLUE = (0x3B, 0x82, 0xF6)


def pixel(x: int, y: int, size: int) -> tuple[int, int, int]:
    u, v = x / size, y / size
    if 0.22 <= u <= 0.60 and 0.62 <= v <= 0.72:
        return XP  # parte preenchida da barra de XP
    if 0.22 <= u <= 0.78 and 0.62 <= v <= 0.72:
        return BLUE
    cx, cy, r = 0.5, 0.40, 0.18
    if (u - cx) ** 2 + (v - cy) ** 2 <= r * r and not ((u - cx) ** 2 + (v - cy) ** 2 <= (r * 0.55) ** 2):
        return XP  # anel da missão
    return BG


def png(size: int) -> bytes:
    rows = b"".join(
        b"\x00" + bytes(c for x in range(size) for c in pixel(x, y, size)) for y in range(size)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        (out / f"icon-{size}.png").write_bytes(png(size))
        print(f"{out}/icon-{size}.png")


if __name__ == "__main__":
    main()
