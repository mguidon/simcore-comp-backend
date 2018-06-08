"""
    Defines **async** handlers for socket.io server


    SEE https://pypi.python.org/pypi/python-socketio
    SEE http://python-socketio.readthedocs.io/en/latest/

"""
# pylint: disable=C0111
# pylint: disable=C0103
import socketio

sio = socketio.AsyncServer(async_mode='aiohttp')

@sio.on('connect')
def connect(sid, environ):
    # environ = WSGI evnironment dictionary
    print("connect ", sid, environ)
    return True

@sio.on('test')
async def test(sid):
    result = "hello from aiohttp aa"
    await sio.emit('test', data=result, room=sid)

@sio.on('log')
async def log(sid):
    result = "hello from aiohttp aa"
    await sio.emit('log', data=result, room=sid)

@sio.on('register_for_log')
async def register_for_log(sid, data):
    result = "Register_log called for {}".format(data)
    await sio.emit('register_for_log', data=result, room=sid)

@sio.on('disconnect')
def disconnect(sid):
    print('disconnect ', sid)
