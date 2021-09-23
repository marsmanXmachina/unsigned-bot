
import random

from collections import defaultdict

from files_util import load_json, save_json


def choose_best_matches(number, matches):

    best_matches = dict()

    for side, side_matches in matches.items():
        if len(side_matches) == 1:
            best_match = side_matches[0]
        else:
            best_match = random.choice(side_matches)
        best_matches[side] = best_match
    
    best_matches["center"] = int(number)

    return best_matches

def match_unsig(number, numbers):
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


def get_matches(udata1, udata2):

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

def get_prop_layers(unsig_data):
    props = unsig_data.get("properties")

    multipliers = props.get("multipliers")
    colors = props.get("colors")
    rotations = props.get("rotations")
    distributions = props.get("distributions")

    return list(zip(colors, multipliers, rotations, distributions))

def order_by_color(layers):
    ordered = defaultdict(list)

    for layer in layers:
        color = layer[0]
        ordered[color].append(layer)
    
    return ordered

def get_opposite_side(side):
    opposite_sides = {
        "left": "right",
        "right": "left",
        "top": "bottom",
        "bottom": "top"
    }

    return opposite_sides.get(side)

def get_rotations_from_direction(direction):
    return [0, 180] if direction == "vertical" else [90, 270]

def get_side_value(layer, side):
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

def get_black_sides(layer):
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

def side_is_black(layer, side):
    black_sides = get_black_sides(layer)
    return True if side in black_sides else False

def mirror_layer(layer, direction):
    rotation = layer[2]
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