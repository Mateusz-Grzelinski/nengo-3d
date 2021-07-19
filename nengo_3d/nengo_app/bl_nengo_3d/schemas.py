from dataclasses import dataclass
from typing import *

from marshmallow import post_load

import nengo_3d_schemas

@dataclass
class Network:
    objects: dict[str, Any]

class NetworkSchema(nengo_3d_schemas.NetworkSchema):
    @post_load
    def make_user(self, data, **kwargs):
        return data
        return Network(**data)
