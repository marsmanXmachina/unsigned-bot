import math
import colorsys

import re

from utility.files_util import load_json

TOTAL_PIXELS = 16384

red = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,64,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,128,192,192,192,192,192,192,192,192,192,192,192,192,192,192,192,192]
green = [0,0,0,0,64,64,64,64,128,128,128,128,192,192,192,192,0,0,0,0,64,64,64,64,128,128,128,128,192,192,192,192,0,0,0,0,64,64,64,64,128,128,128,128,192,192,192,192,0,0,0,0,64,64,64,64,128,128,128,128,192,192,192,192]
blue = [0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192,0,64,128,192]

COLOR_KEYS = list(zip(red, green, blue)) 

COLOR_HEX_URL = "https://www.color-hex.com"

def step (r,g,b, repetitions=1):
    lum = math.sqrt( .241 * r + .691 * g + .068 * b )
    h, s, v = colorsys.rgb_to_hsv(r,g,b)
    h2 = int(h * repetitions)
    lum2 = int(lum * repetitions)
    v2 = int(v * repetitions)
    if h2 % 2 == 1:
        v2 = repetitions - v2
        lum = repetitions - lum
    return (h2, lum, v2)

COLORS_SORTED = sorted(COLOR_KEYS, key=lambda rgb: step(rgb[0],rgb[1],rgb[2],8))


def rgb_2_hex(rgb: tuple):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def get_color_frequencies(idx: str) -> list:
    unsigs_colors = load_json("json/color_frequencies.json")
    color_frequencies = unsigs_colors.get(str(idx))

    return {tuple([int(n) for n in re.findall('[0-9]+', k)]): v for k,v in color_frequencies.items()}

def get_total_colors(color_frequencies: dict) -> int:
    return len([p for p in color_frequencies.values() if p])

def get_top_colors(color_frequencies: dict, num_ranks=10):
    colors_sorted = sorted(color_frequencies.items(), key=lambda x: x[1], reverse=True)

    return {k: v/TOTAL_PIXELS for k,v in dict(colors_sorted[:num_ranks]).items() if v != 0}

def link_hex_color(color_hex):
    color_hex = color_hex.replace("#", "")
    return f"{COLOR_HEX_URL}/color/{color_hex}"