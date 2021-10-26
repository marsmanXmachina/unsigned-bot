import os
import math
import asyncio
import numpy as np
from PIL import Image, ImageOps, ImageDraw

from utility.files_util import load_json
from deconstruct import order_by_color, get_prop_layers

from colors import TOTAL_PIXELS, COLORS_SORTED, rgb_2_hex, get_color_frequencies

BORDER = 10

DIM = 512
DIM_LIST = list(range(DIM))
U_RANGE = 4294967293
MEAN = np.mean(DIM_LIST)
STD = DIM/6


def load_unsig_data(idx):
    unsigs = load_json("json/unsigs.json")
    return unsigs.get(str(idx))

def norm(x , mean , std):
    p = (np.pi*std) * np.exp(-0.5*((x-mean)/std)**2)
    return p

def scale_make2d(s, dim):
    scaled = np.interp(s, (s.min(), s.max()), (0, U_RANGE))
    two_d = np.tile(scaled, (dim, 1))
    return two_d

#probability and cumulative distribution
p_1d = np.array(norm(DIM_LIST, MEAN, STD)).astype(np.uint32)
c_1d = np.cumsum(p_1d)

#2d arrays
p_2d = scale_make2d(p_1d, DIM)
c_2d = scale_make2d(c_1d, DIM)

#dicts for retrieving values
DISTS = {'Normal': p_2d, 'CDF': c_2d}
CHANNELS = {'Red': 0, 'Green': 1, 'Blue': 2}

def get_distributions(dim):
    dims = list(range(dim))
    dims_mean = np.mean(dims)
    std = dim/6

    p_1d = np.array(norm(dims, dims_mean, std)).astype(np.uint32)
    c_1d = np.cumsum(p_1d)

    p_2d = scale_make2d(p_1d, dim)
    c_2d = scale_make2d(c_1d, dim)

    return {'Normal': p_2d, 'CDF': c_2d}


def gen_layer(mult, dist, rot, c, dists=DISTS):
    n = np.zeros((DIM, DIM, 3)).astype(np.uint32)
    buffer =  mult * np.rot90(dists[dist], k=(rot / 90))
    n[ :, :, c ] = n[ :, :, c ] + buffer

    return n

def add_layer(n, mult, dist, rot, c, dists=DISTS):
    buffer =  mult * np.rot90(dists[dist], k=(rot / 90))
    n[ :, :, c ] = n[ :, :, c ] + buffer

    return n

def image_from_ndarray(n):
    n = np.interp(n, (0, U_RANGE), (0, 255)).astype(np.uint8)
    image = Image.fromarray(n)

    return image

def gen_image_array(unsig_data, dim=DIM):
    props = unsig_data['properties']

    if dim == DIM:
        dists = DISTS
    else:
        dists = get_distributions(dim)

    n = np.zeros((dim, dim, 3)).astype(np.uint32)

    for i in range(unsig_data['num_props']):
        mult = props['multipliers'][i]
        col = props['colors'][i]
        dist = props['distributions'][i]
        rot = props['rotations'][i]

        c = CHANNELS[col]

        n = add_layer(n, mult, dist, rot, c, dists=dists)

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
    with_border = ImageOps.expand(image,border=BORDER,fill='white')
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
        c = CHANNELS[col]

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

async def gen_subpattern(idx):
    PADDING = 150

    COLORS = ["Red", "Green", "Blue"]

    unsig_data = load_unsig_data(idx)

    num_props = unsig_data.get("num_props")

    layers = get_prop_layers(unsig_data)
    ordered_by_color = order_by_color(layers)

    images = list()
    n_res = None

    for color in COLORS:
        n_color = None
        color_layers = ordered_by_color.get(color)
        num_colors = len(ordered_by_color.keys())
        if not color_layers:
            continue

        for layer in color_layers:
            col, mult, rot, dist = layer
            c = CHANNELS[col]

            if n_color is None:
                n_color = gen_layer(mult, dist, rot, c)
            else:
                n_color = add_layer(n_color, mult, dist, rot, c)

            if n_res is None:
                n_res = gen_layer(mult, dist, rot, c)
            else:
                n_res = add_layer(n_res, mult, dist, rot, c)
        else:
            sub_image = generate_image(n_color)
            images.append(sub_image)
    else:
        if num_colors > 1:
            image = generate_image(n_res)
            images.append(image)        

    subpattern = None

    x_offset = PADDING
    y_offset = PADDING  

    for image_idx, image in enumerate(images):
        image = image.rotate(180)
        layer_width, layer_height = image.size
        shift = int(layer_height * 0.8)

        if not subpattern:
            total_width = layer_width+2*PADDING
            if num_colors > 1:
                total_height = 2*PADDING+layer_height+shift*(num_colors)
            else:
                total_height = 2*PADDING+layer_height

            subpattern = Image.new(mode="RGBA", size=(total_width, total_height), color="black")

        mask = Image.new(mode="RGBA", size=subpattern.size)
        mask.paste(image, (x_offset, y_offset))
        image.close()

        subpattern = Image.alpha_composite(subpattern, mask)
        mask.close()

        y_offset += shift
    
    subpattern = subpattern.rotate(180)
    path = f'img/subpattern_{idx}.png'
    subpattern.save(path)
    subpattern.close()


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
            data = unsigs_data.get(str(unsigs[unsig_idx]))
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
        
    unsigs_str = "".join(map(str, unsigs))
    
    path = f"img/grid_{unsigs_str}.png"
    grid.save(path)

def v_fade(step=16):
    n = np.zeros((DIM, DIM)).astype(np.uint8)   

    result = list()
    for i in range(0, 255, step):
        n[:][:] = i
        result.append(Image.fromarray(n.copy()))
    
    n[:][:] = 255
    result.append(Image.fromarray(n.copy()))

    return result

def v_blend(width = 16):
    '''make masks for fading from one image to the next through a vertical sweep.  Does this through numpy slices'''
              
    n = np.zeros((DIM, DIM)).astype(np.uint8)            
    
    result=[Image.fromarray(n.copy())]

    for i in range(int(n.shape[0]/width)+1):
        y=i*(width)
        n[y:y+width][:] = 255

        result.append(Image.fromarray(n.copy()))

    return result

async def gen_animation(idx, mode="fade", backwards=False):
    unsig_data = load_unsig_data(idx)

    props = unsig_data.get("properties")
    num_props = unsig_data.get("num_props")

    images = list()

    n = None
    for i in range(num_props):
        mult = props['multipliers'][i]
        col = props['colors'][i]
        dist = props['distributions'][i]
        rot = props['rotations'][i]
        c = CHANNELS[col]

        if n is None:
            n = gen_layer(mult, dist, rot, c)
        else:
            n = add_layer(n, mult, dist, rot, c)
        
        new_layer = image_from_ndarray(n)
        images.append(new_layer)

    if mode == "blend":
        DURATION_FRAME =  50
    else:
        DURATION_FRAME = 100

    images_faded = list()
    durations = list()
    for i in range(len(images)):
        if i == 0:
            continue
        
        if mode =="blend":
            new_frames = [Image.composite(images[i],images[i-1],mask) for mask in v_blend()]
        else:
            new_frames = [Image.composite(images[i],images[i-1],mask) for mask in v_fade()]

        images_faded.extend(new_frames)

        duration_frames = [DURATION_FRAME] * len(new_frames)
        duration_frames[-1] = 1000
        durations.extend(duration_frames)
    
    images_faded = images_faded[::-1]

    durations[0] = 3000
    durations[-1] = 1000

    if backwards:
        fading_backwards = images_faded[::-1]
        durations_backwards = durations[::-1]

        images_faded.extend(fading_backwards)
        durations.extend(durations_backwards)
    
    base_layer = images[-1]

    base_layer.save(f"img/animation_{idx}.gif", format="GIF",  append_images=images_faded[1:], save_all=True, duration=durations, loop=0)

def delete_image_files(path, suffix="png"):
    for file in os.scandir(path):
        if file.name.endswith(f".{suffix}"):
            os.unlink(file.path)


async def gen_grid_with_matches(best_matches):

    unsigs_data = load_json("json/unsigs.json")

    padding = 50
    margin = 2

    unsig_width, unsig_height = DIM, DIM

    unsig_box_width = unsig_box_height = (unsig_width+2*margin)

    cols = rows = 3

    image_width = unsig_box_width*cols + 2*padding
    image_height = unsig_box_height*rows + 2*padding

    left_x = padding + margin
    top_x = center_x = bottom_x = left_x + unsig_box_width
    right_x = left_x + unsig_box_width * 2

    top_y = margin + padding
    left_y = center_y = right_y = top_y + unsig_box_width
    bottom_y = top_y + unsig_box_width * 2

    positions = {
        "top": (top_x, top_y),
        "left": (left_x, left_y),
        "right": (right_x, right_y),
        "bottom": (bottom_x, bottom_y),
        "center": (center_x, center_y)
    }

    grid = Image.new("RGB", (image_width, image_height))

    for side, number in best_matches.items():
        data = unsigs_data.get(str(int(number)))
        image_array = gen_image_array(data)
        image = Image.fromarray(image_array)

        position = positions.get(side)

        grid.paste(image, position)
        image.close()


    unsigs_str = best_matches.get("center")
    path = f"img/matches_{unsigs_str}.png"
    grid.save(path)

async def gen_image_for_tweet(idx):
    unsig_data = load_unsig_data(idx)

    background_size = (4096, 2048)
    background = Image.new("RGB", background_size)

    image_array = gen_image_array(unsig_data, dim=2048)
    image = Image.fromarray(image_array)

    width, height = background_size
    pos_x = int(width/2 - image.width / 2)
    pos_y = 0
    background.paste(image, (pos_x, pos_y))
    image.close()

    path = f'img/tweet_{idx}.png'
    background.save(path)
    background.close()

async def gen_unsig(idx, dim):
    unsig_data = load_unsig_data(idx)

    image_array = gen_image_array(unsig_data, dim)
    image = Image.fromarray(image_array)

    path = f'img/unsig{idx}.png'
    image.save(path)
    image.close()

    return path


async def gen_color_histogram(idx, color_frequencies, sort_colors=False):
    if sort_colors:
        frequencies_sorted = sorted(color_frequencies.items(), key=lambda x: x[1], reverse=True)
    else:
        frequencies_sorted = [(c, color_frequencies.get(c)) for c in COLORS_SORTED]

    PADDING = 25
    COLOR_HEIGHT = 30
    WIDTH = 1080
    HEIGHT = len(frequencies_sorted) * COLOR_HEIGHT + 2 * PADDING
    GRAPHIC_WIDTH = WIDTH - 2 * PADDING

    image = Image.new("RGB", (WIDTH, HEIGHT))

    for i, (color, pixels) in enumerate(frequencies_sorted):
        background = Image.new("RGB", (GRAPHIC_WIDTH, COLOR_HEIGHT-4))

        color_image = ImageDraw.Draw(background)
 
        percentage = pixels / TOTAL_PIXELS

        outline = "#ffffff" if color == (0,0,0) else None
        color_image.rectangle(((0,0), (int(GRAPHIC_WIDTH*percentage), COLOR_HEIGHT-4)), fill=rgb_2_hex(color), outline = outline)

        image.paste(background, (PADDING, i*COLOR_HEIGHT+PADDING))
        background.close()

    if not sort_colors:
        image = image.transpose(Image.ROTATE_90)

    path = f"img/output_colors_{idx}.png"
    image.save(path)
    image.close()

    return path
