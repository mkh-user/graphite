"""Graphite: A clean, embedded graph database engine for Python.

This is graphite module (installation: ``pip install graphitedb``).
You can use it with ``import graphite``.
"""
from warnings import simplefilter

from .graphite_engine import GraphiteEngine
from .instances import Node, Relation
from .migration import Migration
from .query import Direction, QueryBuilder, QueryResult
from .serialization import GraphiteJSONEncoder
from .types import DataType, Field, NodeType, RelationType
from .utils import SecurityWarning

simplefilter('always', SecurityWarning)

__all__ = [
	'GraphiteEngine',
	'Node', 'Relation',
	'Migration',
	'QueryBuilder', 'QueryResult', 'Direction',
	'GraphiteJSONEncoder',
	'DataType', 'Field', 'NodeType', 'RelationType',
	'SecurityWarning', 'engine'
]

def engine() -> GraphiteEngine:
	"""Creates and returns a new [`GraphiteEngine`](../engine) instance.

	Each engine instance maintains its own:

	- Node types
	- Relation types
	- Nodes
	- Relations

	Example:
	    ```python
	    engine = graphite.engine()
	    ```
	"""
	return GraphiteEngine()
