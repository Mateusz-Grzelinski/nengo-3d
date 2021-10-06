import filecmp
import os
import shutil

from .gui import GUI

import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.DEBUG,
    format=f'%(levelname)s:{__name__}:"%(pathname)s:%(lineno)d":%(message)s'
)
