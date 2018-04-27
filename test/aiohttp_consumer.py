"""
    Uses socketio and aiohtttp framework
"""
# pylint: disable=C0103

import os

from aiohttp import web

from async_sio import sio

from setup import rabbit
import asyncio


def create_app(args=()):
    app = web.Application()
    sio.attach(app)

    return app

if __name__ == '__main__':
    app = create_app()
    loop = asyncio.get_event_loop()
    loop.create_task(rabbit())
    web.run_app(app, host="0.0.0.0", port=8080)