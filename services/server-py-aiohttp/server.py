"""
    Uses socketio and aiohtttp framework
"""
# pylint: disable=C0103

import logging
import os

from aiohttp import web
from aiohttp_swagger import setup_swagger

from async_sio import sio
from config import CONFIG

from registry_api import registry_routes
from comp_backend_api import comp_backend_routes

from comp_backend_setup import subscribe
import asyncio

def create_app():
    _CONFIG = CONFIG[os.environ.get('SIMCORE_WEB_CONFIG', 'default')]

    logging.basicConfig(level=_CONFIG.LOG_LEVEL)

    CLIENT_DIR = _CONFIG.SIMCORE_CLIENT_OUTDIR

    _app = web.Application()
    sio.attach(_app)

    # http requests handlers
    async def index(request):
        """Serve the client-side application."""
        logging.debug("index.request:\n %s", request)

        index_path = os.path.join(CLIENT_DIR, 'index.html')
        with open(index_path) as f:
            return web.Response(text=f.read(), content_type='text/html')

    _app.router.add_static('/qxapp', os.path.join(CLIENT_DIR, 'qxapp'))
    _app.router.add_static('/transpiled', os.path.join(CLIENT_DIR, 'transpiled'))
    _app.router.add_static('/resource', os.path.join(CLIENT_DIR, 'resource'))
    _app.router.add_get('/', index)

    _app.router.add_routes(registry_routes)
    _app.router.add_routes(comp_backend_routes)

    setup_swagger(_app)

    return _app

if __name__ == '__main__':
    _CONFIG = CONFIG[os.environ.get('SIMCORE_WEB_CONFIG', 'default')]
    app = create_app()
    loop = asyncio.get_event_loop()
    loop.create_task(subscribe())
    web.run_app(app,
                host=_CONFIG.SIMCORE_WEB_HOSTNAME,
                port=_CONFIG.SIMCORE_WEB_PORT)