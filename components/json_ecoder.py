import dataclasses
import json
import enum


class EnhancedJSONEncoder(json.JSONEncoder):
    """
    >>> json.dumps(foo, cls=EnhancedJSONEncoder)
    """

    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, enum.Enum):
            return o.value
            # return {'enum.Enum': type(o).__name__, o.name: o.value}
        return super().default(o)
