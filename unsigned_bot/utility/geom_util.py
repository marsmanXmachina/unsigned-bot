def get_direction_from_rotation(rotation: int) -> str:
    rotations = {
        0: "vertical",
        90: "horizontal",
        180: "vertical",
        270: "horizontal",
    }
    return rotations.get(rotation)

def get_rotations_from_direction(direction: str) -> list:
    return [0, 180] if direction == "vertical" else [90, 270]

def get_opposite_side(side:str) -> str:
    opposite_sides = {
        "left": "right",
        "right": "left",
        "top": "bottom",
        "bottom": "top"
    }
    return opposite_sides.get(side)