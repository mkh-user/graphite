"""
Example of usage of basic graph algorithms including BFS, etc. in Graphite with internal
`algorithms` module.
"""

from random import randint

from src.graphite import Direction, GraphiteEngine
from src.graphite.algorithms import bfs, neighborhood
# Use this in your code instead:
#from graphite import GraphiteEngine
#from graphite.algorithms import bfs, neighborhood

engine = GraphiteEngine()
engine.define_node("""
node Object
""")
for i in range(30):
	engine.create_node("Object", f"node{i}")

engine.define_relation("""
relation Edge
Object -> Object
""")

for i in range(100):
	engine.create_relation(f"node{i % 30}", f"node{(i + randint(0, 100)) % 30}", "Edge")

# Find ALL possible paths to node10 with less than 6 steps
print(bfs(
	engine,
	"node0",
	"node10",
	stop_at_first=False,
	max_depth=5,
	direction=Direction.BOTH,
	allow_direction_switch=True
))

print(neighborhood(engine, "node0", 4))
# Important algorithms are available directly in engine, so this has same result:
#print(engine.neighborhood("node0", 4))
