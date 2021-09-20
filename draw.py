import os
import math
import asyncio
import numpy as np
from PIL import Image, ImageOps

from files_util import load_json

DIM = 512
BORDER = 10

DIM_LIST = list(range(DIM))
U_RANGE = 4294967293
MEAN = np.mean(DIM_LIST)
STD = DIM/6


def load_unsig_data(idx: str):
    unsigs = load_json("json/unsigs.json")
    return unsigs.get(idx)

def norm(x , mean , std):
    p = (np.pi*std) * np.exp(-0.5*((x-mean)/std)**2)
    return p

def scale_make2d(s):
    scaled = np.interp(s, (s.min(), s.max()), (0, U_RANGE))
    two_d = np.tile(scaled, (DIM, 1))
    return two_d

#probability and cumulative distribution
p_1d = np.array(norm(DIM_LIST, MEAN, STD)).astype(np.uint32)
c_1d = np.cumsum(p_1d)

#2d arrays
p_2d = scale_make2d(p_1d)
c_2d = scale_make2d(c_1d)

#dicts for retrieving values
dists = {'Normal': p_2d, 'CDF': c_2d}
channels = {'Red': 0, 'Green': 1, 'Blue': 2}


def gen_layer(mult, dist, rot, c):
    n = np.zeros((DIM, DIM, 3)).astype(np.uint32)
    buffer =  mult * np.rot90(dists[dist], k=(rot / 90))
    n[ :, :, c ] = n[ :, :, c ] + buffer

    return n

def add_layer(n, mult, dist, rot, c):
    buffer =  mult * np.rot90(dists[dist], k=(rot / 90))
    n[ :, :, c ] = n[ :, :, c ] + buffer

    return n

def image_from_ndarray(n):
    n = np.interp(n, (0, U_RANGE), (0, 255)).astype(np.uint8)
    image = Image.fromarray(n)

    return image

def gen_image_array(unsig_data):
    props = unsig_data['properties']

    n = np.zeros((DIM, DIM, 3)).astype(np.uint32)

    for i in range(unsig_data['num_props']):
        mult = props['multipliers'][i]
        col = props['colors'][i]
        dist = props['distributions'][i]
        rot = props['rotations'][i]

        c = channels[col]

        n = add_layer(n, mult, dist, rot, c)

    n = np.interp(n, (0, U_RANGE), (0, 255)).astype(np.uint8)

    return n    

def generate_image(image_array):
    image = image_from_ndarray(image_array)
    image_with_borders = add_border(image)
    transformed_image = transform_image(image_with_borders)

    return transformed_image

def calc_coeffs(pa, pb):
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])

    A = np.matrix(matrix, dtype="f")
    B = np.array(pb).reshape(8)

    res = np.dot(np.linalg.inv(A.T * A) * A.T, B)

    return np.array(res).reshape(8) 

def transform_image(image):
    image = image.convert('RGBA')

    new_height = 417
    new_width = 726
    new_mid_y = 134

    old_width = old_height = DIM + 2*BORDER

    coeffs = calc_coeffs([(0,new_mid_y), (new_width/2,0), (new_width/2,new_height), (new_width,new_mid_y)], [(0,0), (old_width,0), (0,old_height), (old_width,old_height)])

    transformed_image = image.transform((new_width, new_height), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    
    return transformed_image

def add_border(image):
    with_border = ImageOps.expand(image,border=10,fill='white')
    return with_border


async def gen_evolution(idx, show_single_layers=True, extended=False):

    PADDING = 150

    unsig_data = load_unsig_data(idx)

    props = unsig_data.get("properties")
    num_props = unsig_data.get("num_props")

    if num_props < 2:
        extended = False

    n = None

    images = list()

    for i in range(num_props):
        mult = props['multipliers'][i]
        col = props['colors'][i]
        dist = props['distributions'][i]
        rot = props['rotations'][i]
        c = channels[col]

        if n is None:
            n = gen_layer(mult, dist, rot, c)
        else:
            n = add_layer(n, mult, dist, rot, c)

        if show_single_layers:
            image_array = gen_layer(mult, dist, rot, c)
        else:
            image_array = n

        if extended:
            n_ext = gen_layer(mult, dist, rot, c)
            image_ext = generate_image(n_ext)
            images.append(image_ext)

        image = generate_image(image_array)
        images.append(image)

    if show_single_layers and num_props > 1:
        image = generate_image(n)
        images.append(image)

    evolution = None

    x_offset = PADDING
    y_offset = PADDING

    for image_idx, image in enumerate(images):
        image = image.rotate(180)
        layer_width, layer_height = image.size
        shift = int(layer_height * 0.8)

        if not evolution:
            total_width = layer_width+2*PADDING
            if show_single_layers:
                total_height = 2*PADDING+layer_height+shift*((num_props))
            else:
                if extended:
                    total_width = 2*(layer_width+2*PADDING)

                total_height = 2*PADDING+layer_height+shift*(num_props-1)

            evolution = Image.new(mode="RGBA", size=(total_width, total_height), color="black")
        
        if extended:
            if image_idx % 2 == 0:
                x_offset = PADDING
            else:
                x_offset = 3*PADDING + layer_width

        mask = Image.new(mode="RGBA", size=evolution.size)
        mask.paste(image, (x_offset, y_offset))
        image.close()

        evolution = Image.alpha_composite(evolution, mask)
        mask.close()

        if extended:
            if image_idx % 2 != 0:
                y_offset += shift
        else:
            y_offset += shift

    evolution = evolution.rotate(180)
    path = f'img/evolution_{idx}.png'
    evolution.save(path)
    evolution.close()

    print(f" Saved to => {path}")

async def gen_grid(unsigs: list, cols):

    unsigs_data = load_json("json/unsigs.json")

    num_unsigs = len(unsigs)
    if cols > num_unsigs:
        cols = num_unsigs

    rows = math.ceil(num_unsigs / cols)

    padding = 50
    margin = 5

    unsig_width, unsig_height = DIM, DIM

    image_width = (unsig_width+2*margin)*cols + 2*padding
    image_height = (unsig_height+2*margin)*rows + 2*padding

    grid = Image.new("RGB", (image_width, image_height))

    offset_x = offset_y = padding + margin

    unsig_idx = 0
    for row in range(rows):
        for col in range(cols):
            data = unsigs_data.get(unsigs[unsig_idx])
            image_array = gen_image_array(data)
            image = Image.fromarray(image_array)

            grid.paste(image, (offset_x, offset_y))
            image.close()

            offset_x += 2*margin+unsig_width
            unsig_idx += 1

            if unsig_idx == num_unsigs:
                break 
        
        offset_x = padding + margin
        offset_y += 2*margin+unsig_height
        
    
    unsigs_str = "".join(unsigs)
    path = f"img/grid_{unsigs_str}.png"
    grid.save(path)

def delete_image_files(path):
    for file in os.scandir(path):
        if file.name.endswith(".png"):
            os.unlink(file.path)

