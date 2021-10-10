

def get_direction_from_rotation(rotation):
    rotations = {
        0: "vertical",
        90: "horizontal",
        180: "vertical",
        270: "horizontal",
    }
    return rotations.get(rotation)