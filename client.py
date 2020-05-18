from argparse import ArgumentParser
import asyncio
from datetime import datetime
import os
import uuid

from grpclib.client import Channel

from addressbook_pb2 import Person, AddressBookGetQuery, AddressBookDeleteQuery
from addressbook_grpc import AddressBookStub


def fill_data(person) -> Person:
    name = input("Name (blank to leave as it was): ")
    if name:
        person.name = name

    email = input("Email (blank to leave as it was): ")
    if email:
        person.email = email

    while True:
        number = input("Phone number (blank to finish, \"C\" to clear previous entries): ")
        if not number:
            break

        if number == "C" or number == "С":
            del person.phones[:]
            continue

        phone_number = person.phones.add()
        phone_number.number = number

        number_type = input("Mobile (0), home (1) or work (2)?: ").strip()
        phone_number.type = 0 if number_type not in ["0", "1", "2"] else int(number_type)

    person.last_updated = str(datetime.now())
    return person


def build_person() -> Person:
    new_person = {}
    new_person["id"] = int(uuid.uuid4().time_low)
    new_person["name"] = input("Name: ")
    new_person["email"] = input("Email (blank for none): ")

    while True:
        if "phones" not in new_person:
            new_person["phones"] = []

        number = input("Phone number (blank to finish): ")
        if not number:
            break

        new_phone = {}
        new_phone["number"] = number

        number_type = input("Mobile (0), home (1) or work (2)?: ").strip()
        new_phone["type"] = 0 if number_type not in ["0", "1", "2"] else int(number_type)

        new_person["phones"].append(Person.PhoneNumber(**new_phone))

    new_person["last_updated"] = str(datetime.now())
    return Person(**new_person)


async def main(args) -> None:
    channel = Channel(host="127.0.0.1", port=int(os.environ.get("PORT", 65420)))
    stub = AddressBookStub(channel)

    if "set" in args and args["set"]:
        # stream: Stream[Person, Ok]
        async with stub.Set.open() as stream:
            await stream.send_message(build_person())
            reply = await stream.recv_message()
            print(reply.msg)

    elif "update" in args and args["update"]:
        # stream: Stream[AddressBookGetQuery, Person]
        async with stub.Get.open() as stream:
            await stream.send_message(AddressBookGetQuery(name=input("Search by name: ")))
            replies = [reply async for reply in stream]

            for i, item in enumerate(map(lambda person: [person.name, "---" if not person.phones else person.phones[0].number], replies)):
                print(f"[{i}] {item[0]}: {item[1]}")

            choice = input(":> ").strip()
            if not choice.isdigit():
                return

            person = replies[int(choice)]
            # stream: Stream[Person, Ok]
            async with stub.Update.open() as update_stream:
                await update_stream.send_message(fill_data(person))
                reply = await update_stream.recv_message()
                print(reply.msg)

    elif "get" in args and args["get"]:
        # stream: Stream[AddressBookGetQuery, Person]
        async with stub.Get.open() as stream:
            await stream.send_message(AddressBookGetQuery(name=input("Search by name: ")))
            replies = [reply async for reply in stream]

            for person in replies:
                print(f"Person ID: {person.id}")
                print(f"  Name: {person.name}")
                if person.email:
                    print(f"  E-mail address: {person.email}")

                for phone_number in person.phones:
                    if phone_number.type == Person.PhoneType.MOBILE:
                        print(f"  Mobile phone #: {phone_number.number}")

                    elif phone_number.type == Person.PhoneType.HOME:
                        print(f"  Home phone #: {phone_number.number}")

                    elif phone_number.type == Person.PhoneType.WORK:
                        print(f"  Work phone #: {phone_number.number}")

    elif "delete" in args and args["delete"]:
        # stream: Stream[AddressBookGetQuery, Person]
        async with stub.Get.open() as stream:
            await stream.send_message(AddressBookGetQuery(name=input("Search by name: ")))
            replies = [reply async for reply in stream]

            for i, item in enumerate(map(lambda person: [person.name, "---" if not person.phones else person.phones[0].number], replies)):
                print(f"[{i}] {item[0]}: {item[1]}")

            choice = input(":> ").strip()
            if not choice.isdigit():
                return

            person = replies[int(choice)]
            # stream: Stream[AddressBookDeleteQuery, Ok]
            async with stub.Delete.open() as delete_stream:
                await delete_stream.send_message(AddressBookDeleteQuery(id=person.id))
                reply = await delete_stream.recv_message()
                print(reply.msg)

    channel.close()


if __name__ == "__main__":
    parser = ArgumentParser(description="Address book")
    parser.add_argument("--set", dest="set", action="store_true", required=False, help="Add entry")
    parser.add_argument("--update", dest="update", action="store_true", required=False, help="Update entry")
    parser.add_argument("--get", dest="get", action="store_true", required=False, help="Retrieve entry")
    parser.add_argument("--delete", dest="delete", action="store_true", required=False, help="Remove entry")

    args = parser.parse_args()
    args_dict = args.__dict__

    if not any(args_dict.values()):
        print("Select action:")
        print("[0] Add entry")
        print("[1] Update entry")
        print("[2] Retrieve entry")
        print("[3] Remove entry")
        print("----------------")
        print("[99] Exit")

        args_dict = {
            {
                "0": "set",
                "1": "update",
                "2": "get",
                "3": "delete"
            }.get(input("\n:> ").strip(), "exit"): True
        }

        print()

    asyncio.run(main(args_dict))

