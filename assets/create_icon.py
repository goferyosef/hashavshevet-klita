"""
Run this script once to generate assets/icon.ico.
Requires: pip install Pillow
"""

import os
from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 32,48, 64, 128, 256]
OUT_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")


def make_icon():
    images = []
    for size in SIZES:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background circle — deep blue
        margin = size // 12
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(31, 78, 121, 255),
        )

        # Hebrew letter "ק" centered
        letter = "ק"
        font_size = int(size * 0.52)
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), letter, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size - text_w) // 2 - bbox[0]
        y = (size - text_h) // 2 - bbox[1]
        draw.text((x, y), letter, fill=(255, 255, 255, 255), font=font)

        images.append(img)

    images[0].save(OUT_PATH, format="ICO", sizes=[(s, s) for s in SIZES],
                   append_images=images[1:])
    print(f"Icon saved to {OUT_PATH}")


if __name__ == "__main__":
    make_icon()
