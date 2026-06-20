"""
Graphite: A clean, embedded graph database engine for Python.

This is graphite module (installation: ``pip install graphitedb``).
You can use it with ``import graphite``.
"""
from warnings import simplefilter

from .engine import GraphiteEngine
from .instances import Node, Relation
from .migration import Migration
from .parser import GraphiteParser
from .query import QueryBuilder, QueryResult, Direction
from .serialization import GraphiteJSONEncoder
from .types import DataType, Field, NodeType, RelationType
from .utils import SecurityWarning, engine, node, relation

simplefilter('always', SecurityWarning)

__all__ = [
    'GraphiteEngine',
    'Node', 'Relation',
    'Migration',
    'GraphiteParser',
    'QueryBuilder', 'QueryResult', 'Direction',
    'GraphiteJSONEncoder',
    'DataType', 'Field', 'NodeType', 'RelationType',
    'SecurityWarning', 'engine', 'node', 'relation',
]
