import struct
import sys

from PIL import Image, ImageFilter

THRESHOLD = 16
GAIN = 1.6


def main():
    source = Image.open(sys.argv[1]).convert("L")
    base = source.filter(ImageFilter.MedianFilter(9))
    width, height = source.size
    pixels = source.load()
    background = base.load()
    alpha = Image.new("L", source.size)
    out = alpha.load()
    for y in range(height):
        for x in range(width):
            lift = pixels[x, y] - background[x, y] - THRESHOLD
            out[x, y] = max(0, min(255, int(lift * GAIN * 255 / (255 - background[x, y] or 1))))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.4))
    with open(sys.argv[2], "wb") as f:
        f.write(struct.pack("<HH", width, height))
        f.write(alpha.tobytes())
    if len(sys.argv) > 3:
        alpha.save(sys.argv[3])
    print("{}: {}x{}".format(sys.argv[2], width, height))


if __name__ == "__main__":
    main()
