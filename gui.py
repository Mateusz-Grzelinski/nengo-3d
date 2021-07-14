import logging
import signal
import socket
import time
from dataclasses import dataclass
import sys
import subprocess
import os
from typing import Optional

import nengo

blender_path = r'C:\Users\mat-lp\Documents\magisterka\blender-2.92.0-windows64\blender.exe'
script_path = os.path.dirname(os.path.realpath(__file__))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)

class GUI:
    def __init__(self, filename=None, model: Optional[nengo.Network] = None, local=None, editor=True):
        self.model = model or locals().get("model")  # todo throw error when none
        self.filename = filename or __file__

        os.makedirs('log', exist_ok=True)
        self.server_log = open('log/server.log', 'w')
        self._server_subprocess = subprocess.Popen([sys.executable, "-m", "nengo_3d.server"],
                                                   stdout=self.server_log, stderr=self.server_log,
                                                   # required for windows graceful killing:
                                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                                                   )

        blender_template = os.path.join(script_path, 'blender_template', 'startup.blend')
        self.blender_log = open('log/blender.log', 'w')
        self._blender_subprocess = subprocess.Popen([blender_path, '--addons', 'bl_nengo_3d', blender_template],
                                                    stdout=self.blender_log, stderr=self.blender_log,
                                                    env=os.environ)

    def start(self):
        pass
        # connect to server as client
        # _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # _sock.setblocking(True)
        # _sock.connect(('localhost', 6001))
        # self.model.all_objects
        # message = pickle.dumps(model)
        # message = b'test'
        # _sock.send(message)

    def shutdown(self):
        e = self._blender_subprocess.wait()
        logger.info(f'blender finished with code: {e}')
        # gracefully kills server: note SIGTERM is posix so does not work on windows
        self._server_subprocess.send_signal(signal.CTRL_BREAK_EVENT)
        e = self._server_subprocess.wait()
        logger.info(f'server finished with code: {e}')
        self.blender_log.close()
        self.server_log.close()


if __name__ == '__main__':
    model = nengo.Network()
    g = GUI()
    # time.sleep(3)
    # g.start()
    g.shutdown()
