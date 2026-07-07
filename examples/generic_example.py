"""
Runs a generic example for Graphite module.
"""
import os
import sys

from datetime import date

sys.path.insert(0, os.path.abspath('..'))
from src import graphite
# Use this in your code instead:
#import graphite

engine = graphite.engine()

# Define schema
engine.define_node("""
node Person
name: string
age: int
""")
engine.define_node("""
node Object
price: int
""")

engine.define_relation("""
relation FRIEND both
Person - Person
since: date
""")

# Or use helper functions
#engine.parse(node("User", name="string", age="int"))

engine.parse("""
node User from Person
id: string
""")
engine.parse("""
relation OWNER reverse OWNED_BY
Person -> Object
since: date
""")

# Create nodes
engine.create_node("User", "user1", "John", 25, "john_1")
engine.create_node("User", "user2", "Max", 28, "minimum")
engine.create_node("Object", "book", 1000)

# Create relations
engine.create_relation("user1", "user2", "FRIEND", date.today())
engine.create_relation("user1", "book", "OWNER", date.today())
engine.create_relation("book", "user2", "OWNED_BY", date.today())

# Query
result = (engine.query.User
         .where("age > 18")
         .outgoing("FRIEND")
         .where(lambda n: n['name'].startswith('J'))
         .limit(10)
         .ids())

print(result)

user = engine.query.User.first("name", descending=True)
print(user.id if user else "No users found")
