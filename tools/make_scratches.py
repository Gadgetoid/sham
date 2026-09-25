import argparse
import struct

from PIL import Image, ImageFilter

GLASS_ASPECT = 245 / 86


def checkerboard_alpha(source, threshold=16, gain=1.6):
    base = source.filter(ImageFilter.MedianFilter(9))
    pixels = source.load()
    background = base.load()
    alpha = Image.new("L", source.size)
    out = alpha.load()
    for y in range(source.size[1]):
        for x in range(source.size[0]):
            lift = pixels[x, y] - background[x, y] - threshold
            out[x, y] = max(0, min(255, int(lift * gain * 255 / (255 - background[x, y] or 1))))
    return alpha.filter(ImageFilter.GaussianBlur(0.4))


def luminance_alpha(source, blur, gamma, strength):
    softened = source.filter(ImageFilter.GaussianBlur(blur))
    return softened.point(lambda value: int(255 * strength * (value / 255) ** gamma))


def top_right_band(image, width_fraction):
    width = int(image.size[0] * width_fraction)
    height = min(image.size[1], int(width / GLASS_ASPECT))
    return image.crop((image.size[0] - width, 0, image.size[0], height))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("target")
    parser.add_argument("--preview")
    parser.add_argument("--luminance", action="store_true")
    parser.add_argument("--top-right", type=float, default=0)
    parser.add_argument("--blur", type=float, default=1.2)
    parser.add_argument("--gamma", type=float, default=1.4)
    parser.add_argument("--strength", type=float, default=0.8)
    options = parser.parse_args()

    source = Image.open(options.source).convert("L")
    if options.top_right:
        source = top_right_band(source, options.top_right)
    if options.luminance:
        alpha = luminance_alpha(source, options.blur, options.gamma, options.strength)
    else:
        alpha = checkerboard_alpha(source)
    with open(options.target, "wb") as f:
        f.write(struct.pack("<HH", *alpha.size))
        f.write(alpha.tobytes())
    if options.preview:
        alpha.save(options.preview)
    print("{}: {}x{}".format(options.target, *alpha.size))


if __name__ == "__main__":
    main()
