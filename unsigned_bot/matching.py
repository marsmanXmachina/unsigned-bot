"""
Module to find matching unsigs
"""

import os
import random
from collections import defaultdict
from typing import List, Optional

from unsigned_bot.utility.files_util import load_json
from unsigned_bot.utility.geom_util import get_opposite_side, get_rotations_from_direction
from unsigned_bot.deconstruct import get_prop_layers, order_by_color, get_subpattern, format_subpattern
from unsigned_bot import ROOT_DIR


def choose_random_matches(number: str, matches: dict) -> dict:
    """Choose random selection (one unsig per side) from all available matches"""

    random_matches = dict()

    for side, side_matches in matches.items():
        if len(side_matches) == 1:
            random_match = side_matches[0]
        else:
            random_match = random.choice(side_matches)

        random_matches[side] = random_match
    
    random_matches["center"] = int(number)

    return random_matches

def match_unsig(number: str, numbers: list) -> dict:
    """Try to match unsig with given list of unsigs and return all possible matches."""

    unsigs = load_json(f"{ROOT_DIR}/data/json/unsigs.json")

    matches = defaultdict(list)

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
    """
    Try to find matches of each side for two given unsigs.

    Matching algo:
    Check for each color layer with same direction if it matches.
    If there is no color layer with same direction the matching side has to be black for a potential match.
    """

    layers1 = get_prop_layers(udata1) 
    layers2 = get_prop_layers(udata2)

    layers1_ordered = order_by_color(layers1)
    layers2_ordered = order_by_color(layers2)

    matches = list()

    for side in ["top", "left", "right", "bottom"]:

        # get direction from side
        direction = "horizontal" if side == "left" or side == "right" else "vertical"

        for color in ["Red", "Green", "Blue"]:
            color_layers1 = layers1_ordered.get(color)
            color_layers2 = layers2_ordered.get(color)

            num_layers1 = len(color_layers1) if color_layers1 else 0
            num_layers2 = len(color_layers2) if color_layers2 else 0

            # === colors layers for first unsig do NOT exist ===
            if not color_layers1:
                if not color_layers2:
                    continue # potential match because color layers do not exist in both unsigs
                else:
                    if num_layers2 > 1:
                        break # no match because sides of unsig with more than 1 color layer can not be black
                    else:
                        opposite_side = get_opposite_side(side)
                        if side_is_black(color_layers2[0], opposite_side):
                            continue # potential match because both matching sides are black (or not existent)
                        else:
                            break # no match because one side is not black
            
            # === colors layers for first unsig do exist ===
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
                    # === color layers for both unsigs have only one layer ===
                    if num_layers1 == 1 and num_layers2 == 1:

                        layer1 = color_layers1[0]
                        layer2 = color_layers2[0]
                        
                        mirrored = mirror_layer(layer1, direction)

                        if mirrored == layer2:
                            continue # potential match because mirrored layers are identical
                        else:
                            if side_is_black(layer1, side) and side_is_black(layer2, get_opposite_side(side)):
                                continue # potential match because both matching sides are black
                            else:
                                if get_side_value(layer1, side):
                                    if get_side_value(layer1, side) == get_side_value(layer2, get_opposite_side(side)):
                                        continue # potential match because both matching sides have identical color values
                                    else:
                                        break # no match because both matching sides have different color values
                                else:
                                    break # no match because side of first color layer has not a single color value

                    # === color layers for unsig have different number of layers but at least one ===
                    else:
                        for layer in color_layers1:
                            rot = layer[2]
                            rotations_to_match = get_rotations_from_direction(direction)

                            if rot not in rotations_to_match:
                                continue
                            else:
                                if layer in color_layers2:
                                    break # match because layers in relevant direction are identical
                                else:
                                    continue # no match because layers in relevant direction are different
                        else:
                            break # break outer loop cause no match found in inner loop
        else:
            # unsigs match on current side if loop is not interrupted
            matches.append(side)   

    return matches   

def get_side_value(layer: tuple, side: str) -> int:
    """Get single color value of given side if existing"""

    try:
        _, mult, rot, dist = layer
    except:
        return 
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
    """Get black sides of given layer"""
    try:
        _, _, rot, dist = layer
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
    """Check if given side of layer is black"""
    black_sides = get_black_sides(layer)
    return True if side in black_sides else False

def mirror_layer(layer: tuple, direction: str) -> tuple:
    """Change rotation property of given layer if necessary"""

    _, _, rotation, distribution = layer

    # mirrored layer of normal distribution identical with original layer
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

    # convert layer to list to change rotation
    new_layer = list(layer)
    new_layer[2] = new_rotation

    return tuple(new_layer)

def mirror_layers(layers: list, direction: str) -> list:
    """Mirror each layer in given direction"""
    return [mirror_layer(layer, direction) for layer in layers]
    
def rotate_layer(layer: tuple, rotation_diff: int) -> tuple:
    """Rotate layer by given rotation angle"""

    _, _, rotation, distribution = layer

    new_rotation = rotation + rotation_diff
    new_rotation = new_rotation % 180 if distribution == "Normal" else new_rotation % 360
    
    new_layer = list(layer)
    new_layer[2] = new_rotation

    return tuple(new_layer)

def rotate_layers(layers: list, rotation_diff: str) -> list:
    """Rotate each layer by given rotation angle"""
    return [rotate_layer(layer, rotation_diff) for layer in layers]
 
def get_similar_unsigs(number: str, numbers: List[int], structural: Optional[bool] = True) -> dict:
    """
    Get all unsigs from list which look similar to given unsig.

    Options:
        - get unsigs with axial / point symmetry
        - get unsigs with structural similarity (structural=True)
    """

    unsigs = load_json(f"{ROOT_DIR}/data/json/unsigs.json")

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

def check_similarity(u1_data: dict, u2_data: dict, structural: Optional[bool] = True) -> str:
    """Check similarity between two unsigs regarding symmetry and structural similarity (optional)"""

    layers1 = get_prop_layers(u1_data)
    layers2 = get_prop_layers(u2_data)
    
    if check_axial_symmetry(layers1, layers2):
        return "axial_symmetry"

    if check_point_symmetry(layers1, layers2):
        return "point_symmetry"

    if structural:
        if check_structural_similarity(layers1, layers2):
            return "structural_similarity"

def check_axial_symmetry(layers1: list, layers2: list) -> bool:

    for direction in ["horizontal", "vertical"]:
        mirrored = mirror_layers(layers1, direction)
        if sorted(mirrored) == sorted(layers2):
            return True
    else:
        return False 

def check_point_symmetry(layers1: list, layers2: list) -> bool:

    for rotation in [90, 180, 270]:
        rotated = rotate_layers(layers1, rotation)
        if sorted(rotated) == sorted(layers2):
            return True

        # check for combined point and axial symmetry
        mirrored = mirror_layers(rotated, "vertical")    
        if sorted(mirrored) == sorted(layers2):
            return True        
    else:
        return False

def check_structural_similarity(layers1: list, layers2: list) -> bool:
    """Check if layers of two unsigs are similar regarding their subpattern"""

    def check(layers1: list, layers2: list) -> bool: 
        """Check if given unsigs consist of identical subpattern"""

        subpattern1 = get_subpattern(layers1)
        subpattern2 = get_subpattern(layers2)

        formatted2 = format_subpattern(subpattern2)

        subpattern_mutations = get_subpattern_mutations(subpattern1)

        for mutation in subpattern_mutations:
            if set(mutation) == set(formatted2):
                return True
        else:
            return False


    for rotation in [0, 90, 180, 270]:
        rotated = rotate_layers(layers1, rotation)
        if check(rotated, layers2):
            return True

        rotated_mirrored = mirror_layers(rotated, "vertical")    
        if check(rotated_mirrored, layers2):
            return True     
    
    for direction in ["horizontal", "vertical"]:
        mirrored = mirror_layers(layers1, direction)
        if check(mirrored, layers2):
            return True

def get_subpattern_mutations(subpattern: dict) -> list:
    """Get rotated variations of given subpattern"""

    flattened = format_subpattern(subpattern)
    mutations = [flattened]
    
    for i, layers in enumerate(flattened):
        copied_layers = flattened[:] # copy original layers

        rotated = rotate_layers(layers, 180)
        copied_layers[i] = rotated
        formatted = [tuple(sorted(layers)) for layers in copied_layers]
        mutations.append(formatted)

    return mutations

def save_matches_to_file(number: str, matches: dict) -> str:
    """Save matches for given unsig to text file and return path"""
    
    path = f"{ROOT_DIR}/data/matches_{str(number).zfill(5)}.txt"

    with open(path, 'w') as f:
        f.write(f"Matches for unsig{str(number).zfill(5)}\n")

        for side, assets in matches.items():
            f.write("\n")
            f.write(f"=== {side.upper()} ===\n")

            chunk_size = 10
            chunks = [assets[i:i + chunk_size] for i in range(0, len(assets), chunk_size)]
            for chunk in chunks:
                f.write(",".join(str(asset).zfill(5) for asset in chunk))
                f.write("\n")

    return path

def delete_files(path: str, suffix="txt"):
    """Delete all files with given suffix in path"""
    for file in os.scandir(path):
        if file.name.endswith(f".{suffix}"):
            os.unlink(file.path)