"""
Graphite: A clean, embedded graph database engine for Python.

This is graphite module (installation: ``pip install graphitedb``).
You can use it with ``import graphite``.
"""
from warnings import simplefilter

from .types import DataType, Field, NodeType, RelationType
from .instances import Node, Relation
from .serialization import GraphiteJSONEncoder
from .parser import GraphiteParser
from .query import QueryResult, QueryBuilder
from .engine import GraphiteEngine
from .migration import Migration
from .utils import node, relation, engine, SecurityWarning

simplefilter('always', SecurityWarning)

__all__ = [
    'DataType', 'Field', 'NodeType', 'RelationType',
    'Node', 'Relation', 'GraphiteJSONEncoder',
    'GraphiteParser', 'QueryResult', 'QueryBuilder',
    'GraphiteEngine', 'Migration', 'SecurityWarning',
    'node', 'relation', 'engine'
]
