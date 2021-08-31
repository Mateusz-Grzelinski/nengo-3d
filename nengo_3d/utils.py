import itertools
from typing import Any, Generator


def get_value(source: dict, access_path: tuple['str']) -> Any:
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


def get_path(source: dict, access_path: tuple['str']) -> Generator:
    value = source
    try:
        for path in access_path:
            if isinstance(value, dict):
                value = value.get(path)
            else:
                value = getattr(value, path)
            yield value
    except (IndexError, AttributeError):
        return None


def ranges(i):
    for a, b in itertools.groupby(enumerate(i), lambda pair: pair[1] - pair[0]):
        b = list(b)
        yield b[0][1], b[-1][1]


def ranges_str(i, join='-'):
    for start, end in ranges(i):
        yield f'{start}{join}{end}'
