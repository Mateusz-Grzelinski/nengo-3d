import colorsys


def cycle_color(initial_rgb: tuple[float, float, float], step=0.1, shift_type: str = 'h'):
    """Return unique colors by changing hue. """
    shift_type = shift_type.lower()
    assert shift_type in 'hsv'

    i = 1
    col = {}
    col['h'], col['s'], col['v'] = colorsys.rgb_to_hsv(*initial_rgb)
    used = set()
    while True:
        yield colorsys.hsv_to_rgb(col['h'], col['s'], col['v'])
        used.add(col[shift_type])
        while col[shift_type] in used:
            col[shift_type] += step
            if col[shift_type] > 1:
                col[shift_type] -= 1
                i += 1
                # todo introduce limit to colors to avoid overflow error (2**i)
                col[shift_type] += step / 2 ** i
