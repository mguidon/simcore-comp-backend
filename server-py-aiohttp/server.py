"""
    Uses socketio and aiohtttp framework
"""
# pylint: disable=C0103

import logging
import os

from aiohttp import web
from aiohttp_swagger import *

from async_sio import sio
from config import CONFIG

from registry_api import registry_routes
from comp_backend_api import comp_backend_routes


def create_app(args=()):
    _CONFIG = CONFIG[os.environ.get('SIMCORE_WEB_CONFIG', 'default')]

    logging.basicConfig(level=_CONFIG.LOG_LEVEL)

    CLIENT_DIR = _CONFIG.SIMCORE_CLIENT_OUTDIR

    app = web.Application()
    sio.attach(app)

    # http requests handlers
    async def index(request):
        """Serve the client-side application."""
        logging.debug("index.request:\n %s", request)

        index_path = os.path.join(CLIENT_DIR, 'index.html')
        with open(index_path) as f:
            return web.Response(text=f.read(), content_type='text/html')

    app.router.add_static('/qxapp', os.path.join(CLIENT_DIR, 'qxapp'))
    app.router.add_static('/transpiled', os.path.join(CLIENT_DIR, 'transpiled'))
    app.router.add_static('/resource', os.path.join(CLIENT_DIR, 'resource'))
    app.router.add_get('/', index)

    app.router.add_routes(registry_routes)
    app.router.add_routes(comp_backend_routes)

    setup_swagger(app)

    return app

if __name__ == '__main__':
    _CONFIG = CONFIG[os.environ.get('SIMCORE_WEB_CONFIG', 'default')]
    app = create_app()
    web.run_app(app,
                host=_CONFIG.SIMCORE_WEB_HOSTNAME,
                port=_CONFIG.SIMCORE_WEB_PORT)