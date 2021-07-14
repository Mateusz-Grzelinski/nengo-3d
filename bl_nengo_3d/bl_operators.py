import socket

import bpy

from bl_nengo_3d.connection_handler import handle_data
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
        client.sendall('hello world'.encode('utf-8')) # todo
        share_data.client = client
        bpy.app.timers.register(function=handle_data, first_interval=0)
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
        # share_data.client.shutdown()
        share_data.client.close()
        share_data.client = None
        self.report({'INFO'}, 'Disconnected')
        return {'FINISHED'}


classes = (
    ConnectOperator,
    DisconnectOperator,
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    # disconnect()
    unregister_factory()
