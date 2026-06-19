#!/usr/bin/env python3
"""Generate Python logo GIF with a luminous trail along the logo contour."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from svgpathtools import svg2paths2

SVG_PATH = Path(__file__).with_name("python-official.svg")
OUTPUT_GIF = Path(__file__).with_name("python-trace.gif")
OUTPUT_PNG = Path(__file__).with_name("python-logo.png")

SIZE = 256
PADDING = 20
VIEWBOX = 128
SCALE = (SIZE - 2 * PADDING) / VIEWBOX

BLUE = (48, 105, 152, 255)
YELLOW = (255, 212, 59, 255)
SHADOW = (100, 100, 100, 110)
GLOW_CORE = (255, 255, 255, 255)
GLOW_MID = (255, 245, 180, 220)
GLOW_OUTER = (255, 212, 59, 120)

FRAMES = 48
TRAIL_LENGTH = 28
DURATION_MS = 70


def to_canvas(point: complex) -> tuple[float, float]:
    return point.real * SCALE + PADDING, point.imag * SCALE + PADDING


def sample_path(path, count: int) -> list[tuple[float, float]]:
    total = path.length()
    samples: list[tuple[float, float]] = []
    for i in range(count):
        target = (i / count) * total
        low, high = 0.0, 1.0
        for _ in range(24):
            mid = (low + high) / 2
            if path.cropped(0, mid).length() < target:
                low = mid
            else:
                high = mid
        samples.append(to_canvas(path.point(low)))
    return samples


def path_to_polygon(path, count: int = 400) -> list[tuple[float, float]]:
    return [to_canvas(path.point(t)) for t in np.linspace(0, 1, count, endpoint=False)]


def draw_logo(draw: ImageDraw.ImageDraw, paths, attrs) -> None:
    fills = [BLUE, YELLOW, SHADOW]
    for path, attr, fill in zip(paths, attrs, fills + [SHADOW]):
        if attr.get("opacity") == ".444":
            draw.polygon(path_to_polygon(path, 200), fill=SHADOW)
        elif "python-original-a" in (attr.get("fill") or ""):
            draw.polygon(path_to_polygon(path), fill=BLUE)
        elif "python-original-b" in (attr.get("fill") or ""):
            draw.polygon(path_to_polygon(path), fill=YELLOW)


def draw_trail(base: Image.Image, points: list[tuple[float, float]], head: int) -> Image.Image:
    frame = base.copy()
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    total = len(points)

    for offset in range(TRAIL_LENGTH):
        idx = (head - offset) % total
        x, y = points[idx]
        fade = 1.0 - (offset / TRAIL_LENGTH)
        radius_outer = 7 + 3 * fade
        radius_mid = 4 + 2 * fade
        radius_core = 1.5 * fade

        if fade > 0.75:
            color = (*GLOW_CORE[:3], int(255 * fade))
        elif fade > 0.35:
            color = (*GLOW_MID[:3], int(GLOW_MID[3] * fade))
        else:
            color = (*GLOW_OUTER[:3], int(GLOW_OUTER[3] * fade))

        draw.ellipse(
            [x - radius_outer, y - radius_outer, x + radius_outer, y + radius_outer],
            fill=(*GLOW_OUTER[:3], int(GLOW_OUTER[3] * fade * 0.5)),
        )
        draw.ellipse(
            [x - radius_mid, y - radius_mid, x + radius_mid, y + radius_mid],
            fill=color,
        )
        if radius_core > 0.8:
            draw.ellipse(
                [x - radius_core, y - radius_core, x + radius_core, y + radius_core],
                fill=(*GLOW_CORE[:3], int(220 * fade)),
            )

    return Image.alpha_composite(frame, overlay)


def main() -> None:
    if not SVG_PATH.exists():
        raise FileNotFoundError(f"Missing SVG source: {SVG_PATH}")

    paths, attrs, _ = svg2paths2(str(SVG_PATH))
    logo_paths = [paths[0], paths[1], paths[2]]
    logo_attrs = [attrs[0], attrs[1], attrs[2]]

    base = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)
    draw_logo(draw, logo_paths, logo_attrs)
    base.save(OUTPUT_PNG)

    trace_points = sample_path(paths[0], 320) + sample_path(paths[1], 320)

    frames: list[Image.Image] = []
    for frame_idx in range(FRAMES):
        head = int((frame_idx / FRAMES) * len(trace_points))
        frames.append(draw_trail(base, trace_points, head))

    frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=DURATION_MS,
        loop=0,
        disposal=2,
        optimize=True,
    )
    print(f"Created {OUTPUT_GIF} ({OUTPUT_GIF.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
