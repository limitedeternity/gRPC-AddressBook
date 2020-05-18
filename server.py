import asyncio
import os

from grpclib.utils import graceful_exit
from grpclib.server import Server, Stream

from addressbook_pb2 import Person, AddressBookGetQuery, AddressBookDeleteQuery, Ok
from addressbook_grpc import AddressBookBase
from db import AddressBookDB


database = AddressBookDB("addressbook.db")


class AddressBook(AddressBookBase):
    async def Get(self, stream: Stream[AddressBookGetQuery, Person]):
        request = await stream.recv_message()
        assert request is not None
        for person in database.get(request):
            await stream.send_message(person)

    async def Update(self, stream: Stream[Person, Ok]):
        request = await stream.recv_message()
        assert request is not None
        await stream.send_message(database.update(request))

    async def Set(self, stream: Stream[Person, Ok]):
        request = await stream.recv_message()
        assert request is not None
        await stream.send_message(database.set(request))

    async def Delete(self, stream: Stream[AddressBookDeleteQuery, Ok]):
        request = await stream.recv_message()
        assert request is not None
        await stream.send_message(database.delete(request))


async def main(*, host: str = "127.0.0.1", port: int = int(os.environ.get("PORT", 65420))) -> None:
    server = Server([AddressBook()])

    with graceful_exit([server]):
        await server.start(host, port)
        print(f"Serving on {host}:{port}")
        await server.wait_closed()

    database.connection.close()
    print("Terminated")


if __name__ == "__main__":
    asyncio.run(main())

