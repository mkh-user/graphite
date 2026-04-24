# Quick Start

This page shows how to install Graphite and use it in your Python project.

## Installation

### Method 1: From PyPI (Recommended)

You can get Graphite from **Python Package Index** (PyPI) with `graphitedb` name:

```shell
pip install graphitedb
```

This command will install latest version of Graphite on your device (or virtual environment).
You can find more information about installing python packages [here](https://docs.python.org/3/installing/index.html).

### Method 2: Build From Source

You can build Graphite from source and then install it:
- [Install Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [Install Python](https://www.python.org/downloads/)
- Clone [GitHub Repository](https://github.com/mkh-user/graphite):
```shell
git clone https://github.com/mkh-user/graphite.git
```
- Install `build` package:
```shell
pip install build
```
- Run build command in repository root:
```shell
python -m build
```
- Install package with `pip`:
```shell
# Replace 0.2 with correct version:
pip install ./dist/graphitedb-0.2-py3-none-any.whl
```

### Method 3: Use source (Not recommended)

You can use Graphite without building it, this can be done with a *git submodule* or a regular subfolder in your project
directory. Clone [GitHub repository](https://github.com/mkh-user/graphite) or download it as zip.
Then copy Graphite module (in `src/graphite`) into your project and install requirements:
```shell
# Copy "requirements.txt" into your project and then:
pip install -r requirements.txt
# You can remove this file now:
rm requirements.txt
```

> **Note:**  
> You will need to import Graphite from module path in this method: `import path.to.graphite as graphite`

---

## Usage example

Once you installed Graphite, you can use it in your Python project:

```python
import graphite
```

> **Note:**  
> If you use source instead of `pip` package import with source path: `import path.to.graphite as graphite`

This is a usage example of Graphite:

```python
"""
A complete example of DSL loading with Graphite.
"""

import graphite

# Create a new engine
engine = graphite.engine()

complete_dsl = """
# Lines starting with # will be ignored as comment.

# Define node types
node Person
name: string
age: int

node User from Person
id: string
email: string

node Object

node Book from Object
title: string
n_pages: int

node Car from Object
model: string
year: int

# Define relation types
relation FRIEND both
Person - Person
since: date

relation OWNER reverse OWNED_BY
Person -> Object
since: date
purchased_at: date

relation AUTHOR reverse AUTHORED_BY
Person -> Book
year: int

# Create node instances
User, user_1, "Joe Doe", 32, "joe4030", "joe@email.com"
User, user_2, "Jane Smith", 28, "jane28", "jane@email.com"
User, user_3, "Bob Wilson", 45, "bob45", "bob@email.com"
User, user_4, "Alice Brown", 22, "alice22", "alice@email.com"

Book, book_1, "The Great Gatsby", 180
Book, book_2, "Python Programming", 450
Book, book_3, "Graph Databases", 320

Car, car_1, "Toyota Camry", 2020
Car, car_2, "Honda Civic", 2018

# Create relation instances
user_1 -[FRIEND, 2020-05-15]- user_2
user_1 -[FRIEND, 2019-08-22]- user_3
user_2 -[FRIEND, 2021-01-10]- user_4

user_1 -[OWNER, 2021-03-01, 2021-02-15]-> car_1
user_2 -[OWNER, 2019-06-20, 2019-05-10]-> book_1
user_3 -[OWNER, 2022-11-05, 2022-10-20]-> book_2

user_1 -[AUTHOR, 2020]-> book_3
user_2 -[AUTHOR, 2021]-> book_2

# Alternative syntax (reverse relation)
book_1 -[OWNED_BY, 2019-06-20, 2019-05-10]-> user_2
car_2 -[OWNED_BY, 2018-12-01, 2018-11-15]-> user_4
"""

# Load all with one call
engine.load_dsl(complete_dsl)

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

Documentation is available in Three sections:

- **Introduction:** Know logical design of Graphite to use its power.
- **References:** Detailed information about all available tools in Graphite.
- **Developer Guides:** Information about setup, configure, use, or even improve Graphite behind the scene.

Documentation navigates you step by step as far as you want to know. Now you can go to the next page to continue
learning about Graphite and start production use when you want.
