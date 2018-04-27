"""
    Uses socketio and aiohtttp framework
"""
# pylint: disable=C0103

import logging
import os

from aiohttp import web
from aiohttp_swagger import *

from async_sio import sio

from director_api import director_routes

def create_app(args=()):
    logging.basicConfig(level=logging.DEBUG)

    app = web.Application()
    sio.attach(app)

    app.router.add_routes(director_routes)
    
    return app

if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=8010)