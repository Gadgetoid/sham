import argparse
import math
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def taper(t):
    return math.sin(math.pi * t) ** 0.6


def stroke_points(rng, start, angle, length, bend, steps):
    x, y = start
    points = [(x, y)]
    step = length / steps
    for _ in range(steps):
        angle += bend + rng.normal(0, 0.01)
        x += math.cos(angle) * step
        y += math.sin(angle) * step
        points.append((x, y))
    return points


def draw_stroke(canvas, points, width, intensity, rng, gap_chance):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    pad = int(width) + 2
    left = max(0, int(min(xs)) - pad)
    top = max(0, int(min(ys)) - pad)
    right = min(canvas.shape[1], int(max(xs)) + pad)
    bottom = min(canvas.shape[0], int(max(ys)) + pad)
    if right <= left or bottom <= top:
        return
    layer = Image.new("L", (right - left, bottom - top))
    draw = ImageDraw.Draw(layer)
    segments = len(points) - 1
    broken = False
    for index in range(segments):
        if rng.random() < gap_chance:
            broken = not broken
        if broken:
            continue
        t = (index + 0.5) / segments
        flicker = 0.7 + 0.3 * rng.random()
        value = int(255 * intensity * taper(t) * flicker)
        a = (points[index][0] - left, points[index][1] - top)
        b = (points[index + 1][0] - left, points[index + 1][1] - top)
        draw.line([a, b], fill=value, width=max(1, round(width * (0.6 + 0.4 * taper(t)))))
    region = canvas[top:bottom, left:right]
    np.maximum(region, np.asarray(layer, dtype=np.float32) / 255, out=region)


def random_point(rng, width, height, margin):
    return rng.uniform(-margin, width + margin), rng.uniform(-margin, height + margin)


def hairlines(canvas, rng, count, scale, grain_angle):
    height, width = canvas.shape
    for _ in range(count):
        angle = grain_angle + rng.normal(0, 0.5)
        length = rng.uniform(0.15, 0.7) * width
        points = stroke_points(rng, random_point(rng, width, height, 0.2 * width), angle, length,
                               rng.normal(0, 0.0015), 60)
        intensity = rng.uniform(0.2, 0.5) if rng.random() < 0.85 else rng.uniform(0.6, 0.95)
        draw_stroke(canvas, points, rng.uniform(0.8, 1.8) * scale, intensity, rng, 0.04)


def scuffs(canvas, rng, clusters, scale):
    height, width = canvas.shape
    for _ in range(clusters):
        centre = random_point(rng, width, height, 0)
        heading = rng.uniform(0, math.pi)
        spread = rng.uniform(15, 60) * scale
        for _ in range(rng.integers(4, 14)):
            start = (centre[0] + rng.normal(0, spread), centre[1] + rng.normal(0, spread * 0.5))
            length = rng.uniform(10, 45) * scale
            points = stroke_points(rng, start, heading + rng.normal(0, 0.08), length, rng.normal(0, 0.005), 8)
            draw_stroke(canvas, points, rng.uniform(0.7, 1.3) * scale, rng.uniform(0.15, 0.5), rng, 0.08)


def swirls(canvas, rng, count, scale):
    height, width = canvas.shape
    for _ in range(count):
        cx, cy = random_point(rng, width, height, 0.3 * width)
        radius = rng.uniform(0.1, 0.6) * width
        sweep = rng.uniform(0.15, 0.6)
        base = rng.uniform(0, 2 * math.pi)
        for ring in range(rng.integers(3, 12)):
            r = radius + rng.normal(0, 25 * scale)
            a0 = base + rng.normal(0, 0.08)
            steps = 40
            points = [(cx + math.cos(a0 + sweep * i / steps) * r, cy + math.sin(a0 + sweep * i / steps) * r)
                      for i in range(steps + 1)]
            draw_stroke(canvas, points, rng.uniform(0.8, 1.3) * scale, rng.uniform(0.15, 0.4), rng, 0.06)


def specks(canvas, rng, count, scale):
    height, width = canvas.shape
    image = Image.new("L", (width, height))
    draw = ImageDraw.Draw(image)
    for _ in range(count):
        x, y = rng.uniform(0, width), rng.uniform(0, height)
        r = min(2.5, rng.pareto(4.0) * 0.6 + 0.4) * scale
        value = int(255 * rng.uniform(0.15, 0.7))
        for _ in range(rng.integers(1, 4)):
            dx, dy = rng.normal(0, r, 2)
            draw.ellipse([x + dx - r, y + dy - r * rng.uniform(0.4, 1.0), x + dx + r, y + dy + r], fill=value)
    np.maximum(canvas, np.asarray(image, dtype=np.float32) / 255, out=canvas)


def generate(width, height, seed, supersample, density):
    rng = np.random.default_rng(seed)
    big_w, big_h = width * supersample, height * supersample
    canvas = np.zeros((big_h, big_w), dtype=np.float32)
    grain_angle = rng.uniform(-0.4, 0.4)
    swirls(canvas, rng, int(10 * density), supersample)
    hairlines(canvas, rng, int(90 * density), supersample, grain_angle)
    hairlines(canvas, rng, int(25 * density), supersample, grain_angle + math.pi / 2)
    scuffs(canvas, rng, int(14 * density), supersample)
    specks(canvas, rng, int(350 * density), supersample)
    image = Image.fromarray((canvas * 255).astype(np.uint8))
    return image.resize((width, height), Image.LANCZOS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target")
    parser.add_argument("--preview")
    parser.add_argument("--width", type=int, default=1100)
    parser.add_argument("--height", type=int, default=386)
    parser.add_argument("--seed", type=int, default=2350)
    parser.add_argument("--supersample", type=int, default=3)
    parser.add_argument("--density", type=float, default=1.0)
    parser.add_argument("--blur", type=float, default=0.4)
    parser.add_argument("--gamma", type=float, default=1.0)
    parser.add_argument("--strength", type=float, default=0.9)
    options = parser.parse_args()

    alpha = generate(options.width, options.height, options.seed, options.supersample, options.density)
    if options.blur:
        alpha = alpha.filter(ImageFilter.GaussianBlur(options.blur))
    alpha = alpha.point(lambda value: int(255 * options.strength * (value / 255) ** options.gamma))
    with open(options.target, "wb") as f:
        f.write(struct.pack("<HH", *alpha.size))
        f.write(alpha.tobytes())
    if options.preview:
        alpha.save(options.preview)
    print("{}: {}x{}".format(options.target, *alpha.size))


if __name__ == "__main__":
    main()
