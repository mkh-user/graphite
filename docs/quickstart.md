# Quick Start

This page shows how to install Graphite and use it in your Python project.

Graphite is designed to be easy installable: you can just run `pip install graphitedb` in terminal and done. But you can learn more in this page.

## Installation

Graphite is available at **Python Package Index** ([PyPI](https://pypi.org)) with `graphitedb` name:

```shell
pip install graphitedb
```

This command will install latest version of Graphite on your device (or virtual environment).
You can find more information about installing python packages [here](https://docs.python.org/3/installing/index.html).

!!! Important
    Don't install `graphite` instead of `graphitedb`. Project name is:

    - In PyPI: `graphitedb` -> `pip install graphitedb`
    - In Python: `graphite` -> `import graphite`

## Usage example

Once you installed Graphite, you can use it in your Python project:

```python
import graphite
```

This is a usage example of Graphite:

```python
import graphite
from datetime import date

engine = graphite.engine()

# Use DSL to define types and create data
engine.parse("""
# Node types with 'node '
node Person
    # Indentation is optional
    name: string
    age: int
""")
# Define node types with in-editor hints no parsing cost
engine.define_node("User", ("id", "string"), ("email", "string"), parent="Person")
# parse() can include multiple blocks
engine.parse("""
# You can use node types to control abstractness:
node Object

node Book from Object
    title: string
    n_pages: int

node Car from Object
    model: string
    year: int
""")
engine.define_relation(     # Same with parse():
    "FRIEND",               # relation FRIEND both
    "Person",               #     Person - Person
    "Person",               #     since: date
    ("since", "date"),
    is_bidirectional=True
)
# Relation type blocks are same and node types
engine.parse("""
relation OWNER reverse OWNED_BY
    Person -> Object
    since: date
    purchased_at: date

relation AUTHOR reverse AUTHORED_BY
    Person -> Book
    year: int
""")

# Add data now
# Directly create nodes:
engine.create_node("User", "user_1", "Joe Doe", 32, "joe4030", "joe@email.com")
# Or with parse():
engine.parse("""
User, user_2, "Jane Smith", 28, "jane28", "jane@email.com"
User, user_3, "Bob Wilson", 45, "bob45", "bob@email.com"
User, user_4, "Alice Brown", 22, "alice22", "alice@email.com"

Book, book_1, "The Great Gatsby", 180
Book, book_2, "Python Programming", 450
Book, book_3, "Graph Databases", 320

Car, car_1, "Toyota Camry", 2020
Car, car_2, "Honda Civic", 2018
""")
# And relations:
# Dates can be parsed automatically:
engine.create_relation("user_1", "user_2", "FRIEND", "2020-05-15")
engine.create_relation("user_1", "user_3", "FRIEND", date(2019, 8, 22))
engine.create_relation("user_2", "book_2", "AUTHOR", 2021)
# You can pass parse_fields=True to parse all values from string to correct one:
engine.create_relation("user_1", "book_3", "AUTHOR", "2020", parse_fields=True)
# Is available in DSL too:
engine.parse("""
user_2 -[FRIEND, 2021-01-10]- user_4

user_1 -[OWNER, 2021-03-01, 2021-02-15]-> car_1
user_2 -[OWNER, 2019-06-20, 2019-05-10]-> book_1
user_3 -[OWNER, 2022-11-05, 2022-10-20]-> book_2
""")

print("=== Database Stats ===")
stats = engine.stats()
print(f"Node Types: {stats['node_types']}")
print(f"Relation Types: {stats['relation_types']}")
print(f"Nodes: {stats['nodes']}")
print(f"Relations: {stats['relations']}")

print("\n=== Query Examples ===")

# All users
users = engine.query.User.get()
print(f"All Users ({len(users)}): {[u['name'] for u in users]}")

# Users with more than 30 years age
older_users = engine.query.User.where("age > 30").get()
print(f"\nUsers over 30: {[u['name'] for u in older_users]}")

# Joe Doe books
joe_books = (engine.query.User
              .where(lambda u: u['name'] == "Joe Doe")
              .outgoing("AUTHOR")
              .get())
print(f"\nBooks authored by Joe Doe: {[b['title'] for b in joe_books]}")

# Two steps traverse
friends_of_friends = (engine.query.User
                      .where(lambda u: u['name'] == "Joe Doe")
                      .outgoing("FRIEND")
                      .outgoing("FRIEND")
                      .distinct()
                      .get())
print(f"\nFriends of friends of Joe Doe: {[f['name'] for f in friends_of_friends]}")
```

---

## Learn to use

Documentation navigates you step by step as far as you want to know. Now you can go to the next page to continue learning about Graphite and start production use whenever you want.
