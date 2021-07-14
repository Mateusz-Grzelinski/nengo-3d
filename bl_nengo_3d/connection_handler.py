import bpy
from bl_nengo_3d.share_data import share_data
import logging

logger = logging.getLogger(__file__)

collection_name = 'Sockets'
update_interval = 10


def handle_data():
    data = None

    # In non-blocking mode blocking operations error out with OS specific errors.
    # https://docs.python.org/3/library/socket.html#notes-on-socket-timeouts
    try:
        data = share_data.client.recv(1024)
    except Exception as e:
        logger.exception(e)
        return None  # unregisters handler

    if not data:
        pass
    else:
        logger.debug(f'Incoming: {data}')
        share_data.client.sendall(data)

        # Fetch the 'Sockets' collection or create one. Anything created via sockets will be linked
        # to that collection.
        try:
            collection = bpy.data.collections[collection_name]
        except KeyError:
            collection = bpy.data.collections.new(collection_name)
            bpy.context.scene.collection.children.link(collection)

        if 'cube' in data.decode('utf-8'):
            mesh_data = bpy.data.meshes.new(name='m_cube')
            obj = bpy.data.objects.new('cube', mesh_data)
            collection.objects.link(obj)

        if 'empty' in data.decode('utf-8'):
            empty = bpy.data.objects.new('empty', None)
            empty.empty_display_size = 2
            empty.empty_display_type = 'PLAIN_AXES'
            collection.objects.link(empty)

        if 'quit' in data.decode('utf-8'):
            share_data.client.close()
            share_data.client = None
            return None # unregisters handler

    return update_interval
