from collections import defaultdict, Counter

from utility.files_util import load_json
from utility.geom_util import get_direction_from_rotation

SUBPATTERN_NAMES = ["no-liner", "post", "triple post", "beam", "triple beam", "diagonal", "hourglass", "rivers", "veins", "bulb", "triple bulb"]

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

def format_subpattern(subpattern: dict) -> list:
    formatted = list()

    for _, color_layers in subpattern.items():
        formatted.append(tuple(sorted(color_layers)))

    return formatted


def get_subpattern_names(subpattern: dict) -> dict:

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

def filter_subs_by_names(subs_counted: dict, subs_filters: list) -> list:
    filtered = list()

    if not subs_filters:
        return filtered

    counted = dict(Counter(subs_filters))

    for num, subs in subs_counted.items():
        if counted.items() == subs.items():
            filtered.append(num)

    return filtered