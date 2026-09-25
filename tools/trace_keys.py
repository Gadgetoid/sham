import math
import sys
from collections import deque

from PIL import Image

RAYS = 192
THRESHOLD = 0.5
DARK_THRESHOLD = 0.76

DARK = (37, 46, 55)
BLUE = (48, 92, 145)
TEAL = (37, 114, 110)

REFERENCE_WIDTH = 1400.0

KEYS = (
    ("main", "left", (234.5, 186.6), (39, 18.5), DARK),
    ("tel", "left", (234.5, 243.3), (39, 18.5), DARK),
    ("cal", "left", (234.5, 300.0), (39, 18.5), DARK),
    ("memo", "left", (234.5, 356.7), (39, 18.5), DARK),
    ("prog", "left", (234.5, 413.4), (39, 18.5), DARK),
    ("light", "left", (237.7, 470.3), (22.5, 15.5), TEAL),
    ("menu", "right", (1098.9, 184.5), (18.5, 18.5), DARK),
    ("power", "right", (1179.0, 184.5), (22, 15.5), TEAL),
    ("up", "right", (1167.4, 258.9), (38, 34.5), BLUE),
    ("down", "right", (1166.7, 342.7), (37.5, 34), BLUE),
    ("esc", "right", (1100.4, 396.0), (25.5, 25.5), DARK),
    ("enter", "right", (1169.5, 436.0), (39, 39), DARK),
)


def is_glass(pixel):
    r, g, b = pixel
    return 65 < g < 125 and r < 85 and g > r + 18 and g > b + 8


def find_glass(image):
    width, height = image.size
    pixels = image.load()
    step = 4
    seen = set()
    best = None
    for y in range(0, height, step):
        for x in range(0, width, step):
            if (x, y) in seen or not is_glass(pixels[x, y]):
                continue
            queue = deque([(x, y)])
            seen.add((x, y))
            box = [x, y, x, y]
            count = 0
            while queue:
                cx, cy = queue.popleft()
                count += 1
                box = [min(box[0], cx), min(box[1], cy), max(box[2], cx), max(box[3], cy)]
                for nx, ny in ((cx + step, cy), (cx - step, cy), (cx, cy + step), (cx, cy - step)):
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and is_glass(pixels[nx, ny]):
                        seen.add((nx, ny))
                        queue.append((nx, ny))
            if best is None or count > best[0]:
                best = (count, box)
    return best[1]


def sample(pixels, width, height, x, y):
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - x0, y - y0
    result = [0.0, 0.0, 0.0]
    for dx, dy, weight in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        px = min(width - 1, max(0, x0 + dx))
        py = min(height - 1, max(0, y0 + dy))
        for channel in range(3):
            result[channel] += pixels[px, py][channel] * weight
    return result


def chroma(colour, key):
    if key == BLUE:
        return colour[2] - colour[0]
    return colour[1] - colour[0]


def coverage(colour, background, key):
    if key in (BLUE, TEAL):
        return (chroma(colour, key) - chroma(background, key)) / ((chroma(key, key) - chroma(background, key)) or 1.0)
    axis = [k - b for k, b in zip(key, background)]
    length = sum(a * a for a in axis) or 1.0
    return sum((c - b) * a for c, b, a in zip(colour, background, axis)) / length


def ellipse_radius(half, angle):
    return 1.0 / math.sqrt((math.cos(angle) / half[0]) ** 2 + (math.sin(angle) / half[1]) ** 2)


def trace(image, centre, half, key):
    width, height = image.size
    pixels = image.load()
    ring = [sample(pixels, width, height, centre[0] + math.cos(a) * ellipse_radius(half, a) * 1.45,
                   centre[1] + math.sin(a) * ellipse_radius(half, a) * 1.45)
            for a in (i * math.tau / 48 for i in range(48))]
    ring.sort(key=lambda c: sum(c))
    background = ring[len(ring) * 2 // 3]
    threshold = THRESHOLD if key in (BLUE, TEAL) else DARK_THRESHOLD
    outline = []
    for ray in range(RAYS):
        angle = ray * math.tau / RAYS
        dx, dy = math.cos(angle), math.sin(angle)
        radius = ellipse_radius(half, angle)
        steps = []
        distance = radius * 0.3
        while distance <= radius * 1.45:
            steps.append((distance, coverage(sample(pixels, width, height, centre[0] + dx * distance, centre[1] + dy * distance), background, key)))
            distance += 0.25
        found = radius
        for index in range(len(steps) - 1, 0, -1):
            inner, outer = steps[index - 1], steps[index]
            if inner[1] >= threshold > outer[1]:
                t = (inner[1] - threshold) / (inner[1] - outer[1])
                found = inner[0] + (outer[0] - inner[0]) * t
                break
        outline.append((centre[0] + dx * found, centre[1] + dy * found))
    smoothed = []
    for i in range(RAYS):
        xs = sorted(outline[(i + j) % RAYS][0] for j in (-2, -1, 0, 1, 2))
        ys = sorted(outline[(i + j) % RAYS][1] for j in (-2, -1, 0, 1, 2))
        smoothed.append((sum(xs[1:4]) / 3, sum(ys[1:4]) / 3))
    return smoothed


def fit_circle(points):
    for _ in range(3):
        sums = [[0.0] * 4 for _ in range(3)]
        for x, y in points:
            row = (x, y, 1.0)
            target = -(x * x + y * y)
            for i in range(3):
                for j in range(3):
                    sums[i][j] += row[i] * row[j]
                sums[i][3] += row[i] * target
        for column in range(3):
            pivot = max(range(column, 3), key=lambda r: abs(sums[r][column]))
            sums[column], sums[pivot] = sums[pivot], sums[column]
            for row in range(3):
                if row != column:
                    factor = sums[row][column] / sums[column][column]
                    sums[row] = [a - factor * b for a, b in zip(sums[row], sums[column])]
        d, e, f = (sums[i][3] / sums[i][i] for i in range(3))
        cx, cy = -d / 2, -e / 2
        radius = math.sqrt(cx * cx + cy * cy - f)
        residuals = sorted(abs(math.hypot(x - cx, y - cy) - radius) for x, y in points)
        limit = max(0.5, residuals[len(residuals) // 2] * 2.5)
        points = [(x, y) for x, y in points if abs(math.hypot(x - cx, y - cy) - radius) <= limit]
    return cx, cy, radius


def median(values):
    values = sorted(values)
    return values[len(values) // 2]


def fit_pill(points):
    cx = median([x for x, y in points])
    cy = median([y for x, y in points])
    left = median(sorted(x for x, y in points if abs(y - cy) < 3)[:6])
    top = median(sorted(y for x, y in points if abs(x - cx) < 6)[:6])
    bottom = median(sorted(y for x, y in points if abs(x - cx) < 6)[-6:])
    centre_y = (top + bottom) / 2
    half_h = (bottom - top) / 2
    right = median(sorted(x for x, y in points if abs(y - cy) < 3)[-6:])
    return (left + right) / 2, centre_y, (right - left) / 2, half_h


def fit_arrows(up, down):
    arc = [p for p in up + down if p[0] < median([x for x, y in up + down])]
    cx, cy, radius = fit_circle(arc)
    right_edge = median(sorted(x for x, y in up + down)[-24:])
    up_bottom = median(sorted(y for x, y in up)[-10:])
    down_top = median(sorted(y for x, y in down)[:10])
    return right_edge, (up_bottom + down_top) / 2, radius + (cx - right_edge) * 0, down_top - up_bottom, cx, cy


def main():
    image = Image.open(sys.argv[1]).convert("RGB")
    output = sys.argv[2]
    left, top, right, bottom = find_glass(image)
    glass_h = bottom - top
    scale = 282.0 / glass_h
    pixels_per_reference = image.size[0] / REFERENCE_WIDTH
    lines = [
        "#pragma once",
        "",
        "struct TracedKey {",
        "    const char *name;",
        "    bool right;",
        "    int count;",
        "    const float *points;",
        "};",
        "",
    ]
    names = []
    traced = {}
    for name, anchor, centre, half, colour in KEYS:
        centre_px = (centre[0] * pixels_per_reference, centre[1] * pixels_per_reference)
        half_px = (half[0] * pixels_per_reference, half[1] * pixels_per_reference)
        points = trace(image, centre_px, half_px, colour)
        origin = right if anchor == "right" else left
        traced[name] = [((x - origin) * scale, (y - top) * scale) for x, y in points]
        values = []
        for x, y in points:
            values.append("{:.2f}f".format((x - origin) * scale))
            values.append("{:.2f}f".format((y - top) * scale))
        lines.append("static const float traced_{}[] = {{".format(name))
        for start in range(0, len(values), 12):
            lines.append("    " + ", ".join(values[start:start + 12]) + ",")
        lines.append("};")
        lines.append("")
        names.append((name, anchor))
    for name in ("menu", "esc", "enter"):
        cx, cy, radius = fit_circle(traced[name])
        lines.append("static const float fit_{}[] = {{ {:.2f}f, {:.2f}f, {:.2f}f }};".format(name, cx, cy, radius))
    cx, cy, half_w, half_h = fit_pill(traced["power"])
    lines.append("static const float fit_power[] = {{ {:.2f}f, {:.2f}f, {:.2f}f, {:.2f}f }};".format(cx, cy, half_w, half_h))
    edge, gap_y, radius, gap, arc_x, arc_y = fit_arrows(traced["up"], traced["down"])
    lines.append("static const float fit_arrows[] = {{ {:.2f}f, {:.2f}f, {:.2f}f, {:.2f}f, {:.2f}f, {:.2f}f }};".format(
        edge, gap_y, radius, gap, arc_x, arc_y))
    lines.append("")
    lines.append("static const TracedKey traced_keys[] = {")
    for name, anchor in names:
        lines.append('    {{ "{}", {}, {}, traced_{} }},'.format(name, "true" if anchor == "right" else "false", RAYS, name))
    lines.append("};")
    with open(output, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("glass {}x{} at {},{}; {} keys -> {}".format(right - left, glass_h, left, top, len(names), output))


if __name__ == "__main__":
    main()
