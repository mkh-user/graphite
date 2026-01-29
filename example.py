import graphite

# =============== EXAMPLE COMPLETE DSL LOADING ===============

# Complete example of dsl loading
def example_complete_dsl_loading():
	engine = graphite.engine()

	complete_dsl = """
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

	return engine
