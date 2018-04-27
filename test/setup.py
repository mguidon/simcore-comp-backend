from aio_pika import connect, IncomingMessage, ExchangeType
from async_sio import sio

async def on_message(message: IncomingMessage):
    with message.process():
        print("[x] %r" % message.body)
        await sio.emit("log", data=message.body)

async def rabbit():
    # Perform connection
    connection = await connect(
        "amqp://guest:guest@localhost/"#, loop=loop#
    )

    # Creating a channel
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    logs_exchange = await channel.declare_exchange(
        'logs',
        ExchangeType.FANOUT
    )

    # Declaring queue
    queue = await channel.declare_queue(exclusive=True)

    # Binding the queue to the exchange
    await queue.bind(logs_exchange)

    # Start listening the queue with name 'task_queue'
    await queue.consume(on_message)