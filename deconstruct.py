from collections import defaultdict

from files_util import load_json
from geom_util import get_direction_from_rotation

def get_prop_layers(unsig_data: dict) -> list:
    props = unsig_data.get("properties")

    multipliers = props.get("multipliers")
    colors = props.get("colors")
    rotations = props.get("rotations")
    distributions = props.get("distributions")

    return list(zip(colors, multipliers, rotations, distributions))

def order_by_color(layers: list) -> dict:
    ordered = defaultdict(list)

    for layer in layers:
        color = layer[0]
        ordered[color].append(layer)
    
    return ordered


def get_subpattern(layers: list) -> dict:

    layers_by_color = order_by_color(layers)
    
    subpattern = defaultdict(list)        
    for color, color_layers in layers_by_color.items():
        for layer in color_layers:
            layer_formatted = list(layer)
            layer_formatted[0] = None
            subpattern[color].append(tuple(layer_formatted))
    
    return subpattern

def get_subpattern_names(subpattern):

    NAMES_SINGLE = {
        (2,"vertical"): "post",
        (2,"horizontal"): "beam",
        (4,"vertical"): "triple post",
        (4,"horizontal"): "triple beam",
    }

    NAMES_DOUBLE = {
        (1,1): "diagonal",
        (1,2): "hourglass",
        (1,4): "rivers",
        (2,4): "veins",
        (2,2): "bulb",
        (4,4): "triple bulb"
    }

    names = dict()

    for color, layers in subpattern.items():
        if len(layers) == 1:
            layer = layers[0]
            _, mult, rot, dist = layer
            direction = get_direction_from_rotation(rot)
            name = NAMES_SINGLE.get((mult, direction), "no-liner")
        else:
            props = list(zip(*layers))
            mults =  props[1]

            name = NAMES_DOUBLE.get(mults)

        names[color] = name
    
    return names