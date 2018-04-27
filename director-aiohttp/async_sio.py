"""
    Defines **async** handlers for socket.io server


    SEE https://pypi.python.org/pypi/python-socketio
    SEE http://python-socketio.readthedocs.io/en/latest/

"""
# pylint: disable=C0111
# pylint: disable=C0103
import logging
import json
import socketio

sio = socketio.AsyncServer(async_mode='aiohttp')

@sio.on('connect')
def connect(sid, environ):
    # environ = WSGI evnironment dictionary
    print("connect ", sid, environ)
    return True

@sio.on('test')
async def test(sid, data):
    result = "hello from aiohttp aa"
    await sio.emit('test', data=result, room=sid)

@sio.on('disconnect')
def disconnect(sid):
    print('disconnect ', sid)
