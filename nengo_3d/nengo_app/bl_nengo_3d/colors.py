import colorsys


def cycle_color(initial_rgb: tuple[float, float, float], shift_type: str = 'h', max_colors=8):
    """Return unique colors by changing hue. """
    shift_type = shift_type.lower()
    assert shift_type in 'hsv'

    hsv = colorsys.rgb_to_hsv(*initial_rgb)
    col = {
        'h': hsv[0],
        's': hsv[1],
        'v': hsv[2]
    }
    step = 1 / max_colors
    while True:
        yield colorsys.hsv_to_rgb(col['h'], col['s'], col['v'])
        col[shift_type] += step
        if col[shift_type] > 1:
            col[shift_type] -= 1
            # todo introduce limit to colors to avoid overflow error (2**i)
            col[shift_type] += step
