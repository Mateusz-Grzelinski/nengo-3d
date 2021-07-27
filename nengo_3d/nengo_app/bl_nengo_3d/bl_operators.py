import socket
from functools import partial

import bpy

import bl_nengo_3d.schemas as schemas
from bl_nengo_3d.connection_handler import handle_data, handle_network_model
from bl_nengo_3d.share_data import share_data


class ConnectOperator(bpy.types.Operator):
    """Connect to the Nengo 3d server"""

    bl_idname = 'nengo_3d.connect'
    bl_label = 'Connect to server'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return share_data.client is None  # todo

    def execute(self, context):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client.connect(('localhost', 6001))
        except Exception as e:
            self.report({'ERROR'}, f'Nengo 3d connection failed: {e}')
            return {'CANCELLED'}
        client.setblocking(False)
        client.settimeout(0.01)
        share_data.client = client
        req = schemas.Message()
        message = req.dumps({'schema': schemas.NetworkSchema.__name__})

        client.sendall(message.encode('utf-8'))

        handle_data_function = partial(handle_data, nengo_3d=context.window_manager.nengo_3d)
        share_data.handle_data = handle_data_function
        bpy.app.timers.register(function=handle_data_function, first_interval=0.01)
        self.report({'INFO'}, 'Connected to localhost:6001')
        return {'FINISHED'}


class DisconnectOperator(bpy.types.Operator):
    """Disconnect from the Nengo 3d server"""

    bl_idname = 'nengo_3d.disconnect'
    bl_label = 'Disconnect from server'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        share_data.client.shutdown(socket.SHUT_RDWR)
        share_data.client.close()
        share_data.client = None
        self.report({'INFO'}, 'Disconnected')
        return {'FINISHED'}


class NengoCalculateOperator(bpy.types.Operator):
    """Calculate graph drawing"""
    bl_idname = 'nengo_3d.calculate'
    bl_label = 'Recalculate'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return share_data.model_graph

    def execute(self, context):
        nengo_3d = context.window_manager.nengo_3d
        handle_network_model(g=share_data.model_graph, nengo_3d=nengo_3d)
        context.area.tag_redraw()
        return {'FINISHED'}


class NengoSimulateOperator(bpy.types.Operator):
    """Calculate graph drawing"""
    bl_idname = 'nengo_3d.simulate'
    bl_label = 'Recalculate'
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        schema = schemas.Message()
        data_scheme = schemas.Simulation()
        message = schema.dumps(
            {'schema': schemas.Simulation.__name__,
             'data': data_scheme.dump({'action': 'step'})
             })
        share_data.client.sendall(message.encode('utf-8'))
        context.area.tag_redraw()
        return {'FINISHED'}


classes = (
    ConnectOperator,
    DisconnectOperator,
    NengoCalculateOperator,
    NengoSimulateOperator,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    if share_data.handle_data and bpy.app.timers.is_registered(share_data.handle_data):
        bpy.app.timers.unregister(share_data.handle_data)
        share_data.handle_data = None
    if share_data.client:
        share_data.client.shutdown(socket.SHUT_RDWR)
        share_data.client.close()
        share_data.client = None
    unregister_factory()
