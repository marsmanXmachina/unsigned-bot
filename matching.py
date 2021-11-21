
import random

from collections import defaultdict

from unsigned_bot.utility.files_util import load_json
from unsigned_bot.utility.geom_util import get_opposite_side, get_direction_from_rotation, get_rotations_from_direction

from deconstruct import get_prop_layers, order_by_color, get_subpattern, format_subpattern

def choose_best_matches(number: str, matches: dict) -> dict:

    best_matches = dict()

    for side, side_matches in matches.items():
        if len(side_matches) == 1:
            best_match = side_matches[0]
        else:
            best_match = random.choice(side_matches)
        best_matches[side] = best_match
    
    best_matches["center"] = int(number)

    return best_matches

def match_unsig(number: str, numbers: list) -> dict:
    matches = defaultdict(list)

    unsigs = load_json("json/unsigs.json")

    idx = int(number)
    if idx == 0:
        return dict()

    u1 = unsigs.get(str(idx))

    for j in numbers:
        if idx!=j:
            u2 = unsigs.get(str(j))
            matches_sides = get_matches(u1, u2)

            for side in matches_sides:
                matches[side].append(j)

    return matches


def get_matches(udata1: dict, udata2: dict) -> list:

    SIDES = ["top", "left", "right", "bottom"]
    COLORS = ["Red", "Green", "Blue"]

    layers1 = get_prop_layers(udata1) 
    layers2 = get_prop_layers(udata2)

    layers1_ordered = order_by_color(layers1)
    layers2_ordered = order_by_color(layers2)

    matches = list()

    for side in SIDES:

        if side == "left" or side == "right":
            direction = "horizontal"
        else:
            direction = "vertical"
    
        for color in COLORS:
            color_layers1 = layers1_ordered.get(color, None)
            color_layers2 = layers2_ordered.get(color, None)

            num_layers1 = len(color_layers1) if color_layers1 else 0
            num_layers2 = len(color_layers2) if color_layers2 else 0

            if not color_layers1:
                if not color_layers2:
                    continue
                else:
                    if num_layers2 > 1:
                        break
                    else:
                        opposite_side = get_opposite_side(side)
                        if side_is_black(color_layers2[0], opposite_side):
                            continue
                        else:
                            break
            else:
                if not color_layers2:
                    if num_layers1 > 1:
                        break
                    else:
                        if side_is_black(color_layers1[0], side):
                            continue
                        else:
                            break
                else:
                    if num_layers1 == 1 and num_layers2 == 1:

                        layer1 = color_layers1[0]
                        layer2 = color_layers2[0]
                        
                        mirrored = mirror_layer(layer1, direction)

                        if mirrored == layer2:
                            continue
                        else:
                            if side_is_black(layer1, side) and side_is_black(layer2, get_opposite_side(side)):
                                continue
                            else:
                                if get_side_value(layer1, side):
                                    if get_side_value(layer1, side) == get_side_value(layer2, get_opposite_side(side)):
                                        continue
                                    else:
                                        break
                                else:
                                    break
                    else:
                        for layer in color_layers1:
                            rot = layer[2]
                            rotations_to_match = get_rotations_from_direction(direction)

                            if rot not in rotations_to_match:
                                continue
                            else:
                                if layer in color_layers2:
                                    break
                                else:
                                    continue
                        else:
                            break
        else:
            matches.append(side)   

    return matches   

def get_side_value(layer: tuple, side: str):
    try:
        dist = layer[3]
        rot = layer[2]
        mult = layer[1]
    except:
        return list()
    else:
        if dist == "CDF":
            rotations = {
                0: "right",
                90: "top",
                180: "left",
                270: "bottom"
            }
            side_with_value = rotations.get(rot)
            if side_with_value == side:
                return 1 if mult != 0.5 else 0.5
        else:
            return None

def get_black_sides(layer: tuple) -> list:
    try:
        dist = layer[3]
        rot = layer[2]
    except:
        return list()
    else:
        if dist == "CDF":
            rotations = {
                0: "left",
                90: "bottom",
                180: "right",
                270: "top"
            }
            black_side = rotations.get(rot)
            return [black_side]
        else:
            rotations = {
                0: ["left", "right"],
                90: ["top", "bottom"]
            }
            black_sides = rotations.get(rot)
            return black_sides

def side_is_black(layer: tuple, side: str) -> bool:
    black_sides = get_black_sides(layer)
    return True if side in black_sides else False

def mirror_layer(layer: tuple, direction: str) -> tuple:
    rotation = layer[2]
    distribution = layer[3]
    if distribution == "Normal":
        return layer

    if direction == "horizontal":
        if rotation in [0, 180]:
            new_rotation = 0 if rotation == 180 else 180
        else:
            return layer
    else:
        if rotation in [0, 180]:
            return layer
        else:
            new_rotation = 90 if rotation == 270 else 270

    new_layer = list(layer)
    new_layer[2] = new_rotation
    return tuple(new_layer)

def mirror_layers(layers: list, direction: str) -> list:
    mirrored = list()

    for layer in layers:
        mirrored.append(mirror_layer(layer, direction))
    
    return mirrored

def rotate_layer(layer, rotation_diff: int) -> tuple:
    distribution = layer[3]
    rotated = list(layer) 
    if distribution == "Normal":
        rotated[2] = (layer[2] + rotation_diff) % 180
    else:
        rotated[2] = (layer[2] + rotation_diff) % 360

    return tuple(rotated)

def rotate_layers(layers: list, rotation_diff: str) -> list:
    rotated = list()
    for layer in layers:
        rotated.append(rotate_layer(layer, rotation_diff))
    return rotated


def get_similar_unsigs(number, numbers, structural=True):
    unsigs = load_json("json/unsigs.json")

    similar_unsigs = defaultdict(list)

    idx = int(number)
    u1 = unsigs.get(str(idx)) 

    num1_props = u1.get("num_props") 
    if num1_props == 0:
        return 

    for num in numbers:
        if idx!=num:
            u2 = unsigs.get(str(num))
            num2_props = u2.get("num_props") 
            if num1_props != num2_props:
                continue
            else:
                similarity = check_similarity(u1, u2, structural) 
                if similarity:
                    similar_unsigs[similarity].append(num)
    
    return similar_unsigs

def check_similarity(u1_data, u2_data, structural=True):

    layers1 = get_prop_layers(u1_data)
    layers2 = get_prop_layers(u2_data)
    
    if check_axial_symmetry(layers1, layers2):
        return "axial_symmetry"

    if check_point_symmetry(layers1, layers2):
        return "point_symmetry"

    if structural:
        if check_structural_similarity(layers1, layers2):
            return "structural_similarity"

def check_axial_symmetry(layers1, layers2):
    directions = ["horizontal", "vertical"]
    

    for direction in directions:
        mirrored = mirror_layers(layers1, direction)
        if sorted(mirrored) == sorted(layers2):
            return True
    else:
        return False 

def check_point_symmetry(layers1, layers2):
    rotations = [90, 180, 270]

    for rotation in rotations:
        rotated = rotate_layers(layers1, rotation)
        if sorted(rotated) == sorted(layers2):
            return True

        mirrored = mirror_layers(rotated, "vertical")    
        if sorted(mirrored) == sorted(layers2):
            return True        
    else:
        return False

def check_structural_similarity(layers1, layers2):

    def check(layers1, layers2):
        subpattern1 = get_subpattern(layers1)
        subpattern2 = get_subpattern(layers2)

        # formatted1 = format_subpattern(subpattern1)
        formatted2 = format_subpattern(subpattern2)

        subpattern_mutations = get_subpattern_mutations(subpattern1)

        for mutation in subpattern_mutations:
            if set(mutation) == set(formatted2):
                return True
        else:
            return False

    rotations = [0, 90, 180, 270]

    for rotation in rotations:
        rotated = rotate_layers(layers1, rotation)
        if check(rotated, layers2):
            return True

        rotated_mirrored = mirror_layers(rotated, "vertical")    
        if check(rotated_mirrored, layers2):
            return True     
    
    directions = ["horizontal", "vertical"]

    for direction in directions:
        mirrored = mirror_layers(layers1, direction)
        if check(mirrored, layers2):
            return True

def get_subpattern_mutations(subpattern):

    flattened = format_subpattern(subpattern)
    mutations = [flattened]
    
    rotation = 180
    
    for i,layers in enumerate(flattened):
        copied_layers = flattened[:]

        rotated = rotate_layers(layers, rotation)
        copied_layers[i] = rotated
        formatted = [tuple(sorted(layers)) for layers in copied_layers]
        mutations.append(formatted)

    return mutations

