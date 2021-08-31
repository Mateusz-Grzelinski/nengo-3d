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