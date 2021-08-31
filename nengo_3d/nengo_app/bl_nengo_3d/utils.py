from typing import Any


def get_from_path(source: dict, access_path: tuple['str']) -> Any:
    value = source
    try:
        for path in access_path:
            if isinstance(value, dict):
                value = value.get(path)
            else:
                value = getattr(value, path)
        return value
    except (IndexError, AttributeError):
        return None


def recurse_dict(prefix: str, value: dict):
    for k, v in value.items():
        if k.startswith('_'):
            continue
        elif isinstance(v, list):
            continue
        elif isinstance(v, tuple):
            continue
        elif isinstance(v, dict):
            yield from recurse_dict(prefix=k, value=v)
        yield prefix + '.' + k, v


def normalize_precalculated(x: list[float], min_x: float, max_x: float):
    if min_x == max_x:
        min_x -= 1
        max_x += 1
    for i, _x in enumerate(x):
        x[i] = (_x - min_x) / (max_x - min_x)
    return x


def normalize(x: list[float]):
    min_x = min(x) if len(x) == 0 else 0
    max_x = max(x) if len(x) == 0 else 1
    if min_x == max_x:
        min_x = round(min_x - 1)
        max_x = round(max_x + 1)
    for i, _x in enumerate(x):
        x[i] = (_x - min_x) / (max_x - min_x)
    return x, min_x, max_x


def denormalize(x: list[float], min_x: float, max_x: float):
    for i, _x in enumerate(x):
        x[i] = (_x - min_x) / (max_x - min_x)
    return x