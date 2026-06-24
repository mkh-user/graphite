"""
Graphite: A clean, embedded graph database engine for Python.

This is graphite module (installation: ``pip install graphitedb``).
You can use it with ``import graphite``.
"""
from warnings import simplefilter

from .engine import GraphiteEngine
from .instances import Node, Relation
from .migration import Migration
from .query import Direction, QueryBuilder, QueryResult
from .serialization import GraphiteJSONEncoder
from .types import DataType, Field, NodeType, RelationType
from .utils import SecurityWarning, node, relation

simplefilter('always', SecurityWarning)

__all__ = [
	'GraphiteEngine',
	'Node', 'Relation',
	'Migration',
	'QueryBuilder', 'QueryResult', 'Direction',
	'GraphiteJSONEncoder',
	'DataType', 'Field', 'NodeType', 'RelationType',
	'SecurityWarning', 'engine', 'node', 'relation',
]

def engine() -> GraphiteEngine:
	"""Create graphite engine instance"""
	return GraphiteEngine()
