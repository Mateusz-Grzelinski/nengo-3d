from marshmallow import Schema, fields


class Message(Schema):
    schema = fields.Str(required=True)
    data = fields.Field()
    """Based on schema decode the data field. Data can be any Schema"""


class Observe(Schema):
    source = fields.Str(required=True, allow_none=False)
    access_path = fields.Str(required=True)
    sample_every = fields.Int(required=True)
    dt = fields.Float(required=True)


class PlotLines(Schema):
    source = fields.Str(required=True)
    access_path = fields.Str(required=True)
    step = fields.Int(required=True)
    data = fields.List(fields.Field())
    labels = fields.List(fields.Str())


class SimulationSteps(Schema):
    step = fields.Int(strict=True)
    node_name = fields.Str()
    parameters = fields.Dict(keys=fields.Str(),
                             values=fields.List(fields.Field()), default=None)


class Simulation(Schema):
    action = fields.Str()
    until = fields.Int()
    dt = fields.Float(default=0.001)
    sample_every = fields.Int(required=True)
    observe = fields.List(fields.Nested(Observe))
    plot_lines = fields.List(fields.Nested(PlotLines))


class ConnectionSchema(Schema):
    name = fields.Str()
    pre = fields.Str()
    post = fields.Str()
    type = fields.Str(required=True)
    class_type = fields.Str(required=True)
    label = fields.Str(allow_none=True)
    probeable = fields.List(fields.Str())
    size_in = fields.Int()
    size_mid = fields.Int()
    size_out = fields.Int()
    seed = fields.Int(allow_none=True)
    has_weights = fields.Bool(required=True)
    # for now just names of classes:
    function_info = fields.Str()
    solver = fields.Str()
    synapse = fields.Str()
    transform = fields.Str()


class NeuronType(Schema):
    name = fields.Str(required=True)
    probeable = fields.List(fields.Str())
    negative = fields.Bool()
    spiking = fields.Bool()
    # state


class Neurons(Schema):
    probeable = fields.List(fields.Str())
    size_in = fields.Int()
    size_out = fields.Int()


class NodeSchema(Schema):
    # name = fields.Str()
    type = fields.Str(required=True)
    class_type = fields.Str(required=True)
    network_name = fields.Str(required=True)
    name = fields.Str(required=True)
    module = fields.Str(required=True)
    has_vocabulary = fields.Bool(required=True)
    vocabulary_size = fields.Int(required=True, allow_none=True)
    vocabulary = fields.List(fields.Str())
    probeable = fields.List(fields.Str())
    label = fields.Str(allow_none=True)
    size_in = fields.Int()
    size_out = fields.Int()
    seed = fields.Int(allow_none=True)
    n_neurons = fields.Int(allow_none=True)
    neuron_type = fields.Nested(NeuronType, allow_none=True, default=None)
    neurons = fields.Nested(Neurons, allow_none=True, default=None)


class NetworkSchema(Schema):
    file = fields.Str()
    type = fields.Str(required=True)
    network_name = fields.Str(required=True)
    parent_network = fields.Str(required=True)
    module = fields.Str(required=True)
    class_type = fields.Str(required=True)
    n_neurons = fields.Int()
    nodes = fields.Dict(keys=fields.Str(), values=fields.Nested(NodeSchema()))
    connections = fields.Dict(keys=fields.Str(), values=fields.Nested(ConnectionSchema()))
    networks = fields.Dict(keys=fields.Str(), values=fields.Nested(lambda: NetworkSchema(), exclude={'file'}))
