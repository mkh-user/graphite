from graphit import GraphiteDb

db = GraphiteDb()

with open("C:/Users/Mahan/Desktop/Graphite Example.gdbs") as file:
	err = db.parse_struct(file.read())
if err:
	print(err)
	exit(1)

# print(db.struct_overview())

nodes = [
	# ["Person", "user1", ["Mahan", "Khalili", 16]],
	# ["Person", "user2", ["Pouyan", "Khalili", 13]],
	# ["Book", "math", [1200, 200]],
]
relations = [
	# ["FRIEND", "user1", "user2", ["2010-07-12"]],
]

for n in nodes:
	err = db.add_node(n[0], n[1], n[2])
	if err:
		print(err)
		exit(1)
for r in relations:
	err = db.add_relation(r[0], r[1], r[2], r[3])
	if err:
		print(err)
		exit(1)

with open("C:/Users/Mahan/Desktop/Graphite Example.gdb") as file:
	err = db.parse_data(file.read())
if err:
	print(err)
	exit(1)

print(db.nodes_overview())
print(db.relations_overview())

