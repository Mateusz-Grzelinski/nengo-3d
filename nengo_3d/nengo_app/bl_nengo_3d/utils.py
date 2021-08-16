from typing import Generator, Any

import bpy


def redraw_all():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()


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
