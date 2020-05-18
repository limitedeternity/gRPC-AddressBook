import sqlite3

from addressbook_pb2 import Person, AddressBookGetQuery, AddressBookDeleteQuery, Ok


class AddressBookDB:
    def __init__(self, file) -> None:
        self.connection = sqlite3.connect(file)
        self.cursor = self.connection.cursor()

        self.cursor.executescript('''
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS addressbook (
                name TEXT NOT NULL,
                id INTEGER PRIMARY KEY,
                email TEXT DEFAULT NULL,
                last_updated TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS phones (
                id INTEGER NOT NULL,
                number TEXT NOT NULL UNIQUE,
                type INTEGER DEFAULT 0 CHECK (type == 0 OR type == 1 OR type == 2),
                FOREIGN KEY (id)
                    REFERENCES addressbook (id)
                        ON UPDATE CASCADE
                        ON DELETE CASCADE
            );
        ''')

        self.connection.commit()

    def get(self, query: AddressBookGetQuery) -> [Person]:
        return list(
            map(
                lambda person_with_phones: Person(**person_with_phones),
                map(
                    lambda person: {
                        **person,
                        "phones": list(
                            map(
                                lambda row: Person.PhoneNumber(**dict(zip(["number", "type"], row))),
                                self.cursor.execute(
                                    '''SELECT number, type FROM phones WHERE id = ?;''',
                                    (person["id"],)
                                )
                            )
                        )
                    },
                    map(
                        lambda row: dict(zip(["name", "id", "email", "last_updated"], row)),
                        self.cursor.execute(
                            '''SELECT name, id, email, last_updated FROM addressbook WHERE name LIKE ?;''',
                            (f"{query.name}%",)
                        )
                    )
                )
            )
        )

    def update(self, person: Person) -> Ok:
        return self.set(person)

    def set(self, person: Person) -> Ok:
        self.cursor.execute(
            '''INSERT OR REPLACE INTO addressbook (name, id, email, last_updated) VALUES (?, ?, ?, ?);''',
            (person.name, person.id, person.email, person.last_updated)
        )

        for phone in person.phones:
            self.cursor.execute(
                '''INSERT OR REPLACE INTO phones (id, number, type) VALUES (?, ?, ?);''',
                (person.id, phone.number, phone.type)
            )

        self.connection.commit()
        return Ok(msg="Success")

    def delete(self, query: AddressBookDeleteQuery) -> Ok:
        self.cursor.execute(
            '''DELETE FROM addressbook WHERE id = ?;''',
            (query.id,)
        )

        self.connection.commit()
        return Ok(msg="Success")

