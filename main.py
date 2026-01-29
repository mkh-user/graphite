from datetime import date
import graphite

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
#engine.load_dsl(node("User", name="string", age="int"))

engine.load_dsl("""
node User from Person
id: string
""")
engine.load_dsl("""
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

print(engine.query.User.order_by("name").first()["name"])
