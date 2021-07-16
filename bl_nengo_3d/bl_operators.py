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
        client.setblocking(False)
        client.settimeout(0.01)
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
        share_data.client.close()
        share_data.client = None
        self.report({'INFO'}, 'Disconnected')
        return {'FINISHED'}


class DebugConnectionOperator(bpy.types.Operator):
    """Send custom message via socket
    Response will be processed via `connection_handler.handle_data`"""

    bl_idname = 'nengo_3d.connect_debug'
    bl_label = 'Send debug message'
    bl_options = {'REGISTER'}

    message: bpy.props.StringProperty(
        name="Debug Message",
        description="Send any message via socket",
        default="{\"model\":1}"
    )

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "message")

        # if self.val1:
        #     box = layout.box()
        #     box.prop(self, "val2")
        #     box.prop(self, "val3")

    @classmethod
    def poll(cls, context):
        return share_data.client is not None

    def execute(self, context):
        share_data.client.send(self.message.encode('utf-8'))
        return {'FINISHED'}


classes = (
    ConnectOperator,
    DisconnectOperator,
    DebugConnectionOperator
)

register_factory, unregister_factory = bpy.utils.register_classes_factory(classes)


def register():
    register_factory()


def unregister():
    # disconnect()
    unregister_factory()
