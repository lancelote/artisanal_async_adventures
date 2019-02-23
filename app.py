import select
import socket
from collections import deque
from enum import Enum, auto
from typing import *

Address = Tuple[str, int]
Task = TypeVar('Task')

TASKS: Deque[Task] = deque()
WAIT_READ: Dict[socket.socket, Task] = {}
WAIT_SEND: Dict[socket.socket, Task] = {}


def algorithm(n: int) -> int:
    return n + 42


class Action(Enum):
    Read = auto()
    Send = auto()


class Can:
    def __init__(self, action: Action, target: socket.socket):
        self.action = action
        self.target = target

    def __await__(self):
        yield self.action, self.target


def add_task(task: Task) -> None:
    TASKS.append(task)


def run() -> None:
    while any([TASKS, WAIT_SEND, WAIT_READ]):
        while not TASKS:
            can_read, can_send, _ = select.select(WAIT_READ, WAIT_SEND, [])
            for sock in can_read:
                add_task(WAIT_READ.pop(sock))
            for sock in can_send:
                add_task(WAIT_SEND.pop(sock))
        current_task = TASKS.popleft()
        try:
            action, target = current_task.send(None)
        except StopIteration:
            continue
        if action is Action.Read:
            WAIT_READ[target] = current_task
        elif action is Action.Send:
            WAIT_SEND[target] = current_task
        else:
            raise ValueError(f'unexpected action {action}')


async def async_accept(sock: socket.socket) -> Tuple[socket.socket, Address]:
    await Can(Action.Read, sock)
    return sock.accept()


async def async_recv(client: socket.socket, num: int) -> bytes:
    await Can(Action.Read, client)
    return client.recv(num)


async def async_send(client: socket.socket, data: bytes) -> int:
    await Can(Action.Send, client)
    return client.send(data)


async def handler(client: socket.socket) -> None:
    while True:
        request: bytes = await async_recv(client, 100)
        if not request.strip():
            client.close()
            return
        number = int(request)
        result = algorithm(number)
        await async_send(client, f'{result}\n'.encode('ascii'))


async def server(address: Address) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    while True:
        client, client_address = await async_accept(sock)
        print(f'connection from {client_address}')
        add_task(handler(client))


if __name__ == '__main__':
    add_task(server(('localhost', 30303)))
    run()
