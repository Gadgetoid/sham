import json
import sys

WIDTH = 176
HEIGHT = 66
LAT_TOP = 74.0
LAT_BOTTOM = -48.0
SUPERSAMPLE = 4


def project(lon, lat, width, height):
    x = (lon + 180.0) / 360.0 * width
    y = (LAT_TOP - lat) / (LAT_TOP - LAT_BOTTOM) * height
    return x, y


def fill_ring(bitmap, ring, width, height):
    points = [project(lon, lat, width, height) for lon, lat in ring]
    edges = list(zip(points, points[1:] + points[:1]))
    top = max(0, int(min(y for _, y in points)))
    bottom = min(height - 1, int(max(y for _, y in points)) + 1)
    for row in range(top, bottom + 1):
        sample_y = row + 0.5
        crossings = []
        for (x0, y0), (x1, y1) in edges:
            if (y0 <= sample_y < y1) or (y1 <= sample_y < y0):
                crossings.append(x0 + (sample_y - y0) * (x1 - x0) / (y1 - y0))
        crossings.sort()
        for start, end in zip(crossings[0::2], crossings[1::2]):
            first = max(0, int(start + 0.5))
            last = min(width - 1, int(end - 0.5))
            for column in range(first, last + 1):
                bitmap[row * width + column] = 1


def main():
    source = sys.argv[1]
    target = sys.argv[2]
    big_w, big_h = WIDTH * SUPERSAMPLE, HEIGHT * SUPERSAMPLE
    bitmap = bytearray(big_w * big_h)
    for country in json.load(open(source)):
        for ring in country["polygons"]:
            if len(ring) >= 3:
                fill_ring(bitmap, ring, big_w, big_h)
    area = SUPERSAMPLE * SUPERSAMPLE
    levels = bytearray([WIDTH, HEIGHT])
    for y in range(HEIGHT):
        for x in range(WIDTH):
            covered = 0
            for sy in range(SUPERSAMPLE):
                row = (y * SUPERSAMPLE + sy) * big_w + x * SUPERSAMPLE
                covered += sum(bitmap[row:row + SUPERSAMPLE])
            levels.append(min(3, (covered * 3 + area // 2) // area))
    with open(target, "wb") as f:
        f.write(levels)
    land = sum(1 for level in levels[2:] if level == 3)
    print("{}: {}x{}, {} land pixels".format(target, WIDTH, HEIGHT, land))


if __name__ == "__main__":
    main()
