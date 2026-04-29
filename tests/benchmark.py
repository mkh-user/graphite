"""
Advanced benchmark suite for the Graphite embedded graph database.

Usage:
    python benchmark.py [--size N] [--runs M] [--output json|plain]

This script measures the performance of core Graphite operations under
synthetic, configurable workloads. It reports timing statistics and, where
possible, memory usage.
"""

import argparse
import gc
import json
import os
import statistics
import sys
import time
from datetime import date
from typing import Any
from pympler import asizeof

# ---------------------------------------------------------------------------
# Try to import graphite – if it isn't editable, use installed
# ---------------------------------------------------------------------------
try:
	# Add parent directory to path (assumes benchmark is inside the package or next to it)
	sys.path.insert(0, os.path.abspath('..'))
	from src.graphite import(
		DataType, Field, NodeType, RelationType, Node, Relation, QueryBuilder, GraphiteEngine
	)
except ImportError:
	from graphite import (
		DataType, Field, NodeType, RelationType, Node, Relation, QueryBuilder, GraphiteEngine
	)

# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------
def timed_call(func, *args, _iterations: int = 10, _setup=None, **kwargs) -> dict[str, float]:
	"""
	Time a callable over multiple iterations and return summary statistics.
	Runs garbage collection before each iteration to reduce noise.
	"""
	times = []
	for _ in range(_iterations):
		if _setup:
			_setup()
		gc.collect()
		start = time.perf_counter()
		func(*args, **kwargs)
		elapsed = time.perf_counter() - start
		times.append(elapsed)
	if not times:
		return {"mean": 0.0, "min": 0.0, "max": 0.0, "stdev": 0.0, "iterations": 0}
	return {
		"mean": statistics.mean(times),
		"min": min(times),
		"max": max(times),
		"stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
		"iterations": len(times),
	}


def human_bytes(num_bytes: float) -> str:
	"""Convert bytes to a human-readable string."""
	for unit in ("B", "KB", "MB", "GB"):
		if abs(num_bytes) < 1024.0:
			return f"{num_bytes:3.1f} {unit}"
		num_bytes /= 1024.0
	return f"{num_bytes:.1f} TB"


# ---------------------------------------------------------------------------
# Data generation for benchmarks
# ---------------------------------------------------------------------------
# pylint: disable=too-many-locals
def create_benchmark_engine(
	num_node_types: int = 5,
	num_relation_types: int = 3,
	num_nodes: int = 1000,
	num_relations: int = 500,
	inheritance_depth: int = 1,
) -> GraphiteEngine:
	"""
	Build an engine with a synthetic schema and populate it with nodes and relations.
	Returns the populated engine.
	"""
	engine = GraphiteEngine()

	# Define node types with a simple inheritance chain
	for i in range(num_node_types):
		parent = None
		if inheritance_depth > 1 and i > 0:
			# Chain: Type0 -> Type1 -> Type2 ...
			parent = f"NodeType{i-1}"
		fields = [
			         (f"int_field_{j}", "int") for j in range(3)
		         ] + [
			         (f"str_field_{j}", "string") for j in range(2)
		         ] + [
			         ("float_field", "float"),
			         ("date_field", "date"),
			         ("bool_field", "bool"),
		         ]

		engine.define_node(
			f"node NodeType{i}" +
			(f" from {parent}" if parent else "") +
			"\n" +
			"\n".join([f"{field[0]}: {field[1]}" for field in fields])
		)

	# Define relation types
	for i in range(num_relation_types):
		from_type = f"NodeType{i % num_node_types}"
		to_type = f"NodeType{(i+1) % num_node_types}"
		fields = [
			("weight", "float"),
			("label", "string"),
		]
		reverse = f"RevRel{i}" if i % 2 == 0 else None
		bidirectional = not reverse and i % 3 == 0
		engine.define_relation(
			f"relation RelType{i}" +
			(f" reverse RevRel{i}" if reverse else "") +
			(" both" if bidirectional else "") +
			f"\n{from_type}->{to_type}\n" +
			"\n".join([f"{field[0]}: {field[1]}" for field in fields]),
		)

	# Populate nodes
	nodes = []
	for n in range(num_nodes):
		type_idx = n % num_node_types
		node_id = f"node_{n}"
		# Generate some consistent 'random' values
		int_vals = [(n * 31 + j) % 1000 for j in range(3)]
		str_vals = [f"str_{n}_{j}" for j in range(2)]
		float_val = float(n % 100) / 10.0
		# Date as days from 2020-01-01
		date_val = date(2020, 1, 1).toordinal() + n
		date_val = date.fromordinal(date_val)
		bool_val = n % 2 == 0

		values: dict[str, Any] = {
			f"int_field_{j}": int_vals[j] for j in range(3)
		}
		values.update({
			f"str_field_{j}": str_vals[j] for j in range(2)
		})
		values["float_field"] = float_val
		values["date_field"] = date_val.isoformat()  # stored as string, validated later
		values["bool_field"] = bool_val

		node = engine.create_node(f"NodeType{type_idx}", node_id, *values.values())
		nodes.append(node)

	# Populate relations
	for r in range(num_relations):
		rel_type_idx = r % num_relation_types
		rel_type_name = f"RelType{rel_type_idx}"
		rel_type_obj = engine.relation_types[rel_type_name]
		from_id = next(iter(engine.node_by_type[rel_type_obj.from_type])).id
		to_id = next(iter(engine.node_by_type[rel_type_obj.to_type])).id
		values = {"weight": float(r % 100) / 100.0, "label": f"edge_{r}"}
		engine.create_relation(from_id, to_id, rel_type_name, *values.values())

	return engine


# ---------------------------------------------------------------------------
# Benchmark class
# ---------------------------------------------------------------------------
class GraphiteBenchmarks:
	"""Collection of micro-benchmarks for Graphite."""

	def __init__(self, size: int = 5000, runs: int = 10):
		self.size = size  # base scale factor for data
		self.runs = runs
		self.results: dict[str, Any] = {}

	def _run_benchmark(self, name: str, func, *args, _setup=None, **kwargs):
		"""Execute a timed call and store the result."""
		stats = timed_call(func, *args, _iterations=self.runs, _setup=_setup, **kwargs)
		self.results[name] = stats
		return stats

	def benchmark_all(self):
		"""Run all benchmarks and collect results."""
		self.benchmark_schema_definition()
		self.benchmark_node_creation()
		self.benchmark_relation_creation()
		self.benchmark_queries()
		self.benchmark_serialization()
		self.benchmark_dsl_parsing()
		self.benchmark_memory()
		return self.results

	# ---------- Schema definition ----------
	def benchmark_schema_definition(self):
		"""Define many node and relation types repeatedly."""
		n_types = max(1, self.size // 10)
		# Node types
		def define_node_types():
			eng = GraphiteEngine()
			for i in range(n_types):
				parent = None
				if i % 5 == 0 and i > 0:
					parent = f"node_type_{i-1}"
				fields = "int_field: int\nstr_field: string\nfloat_field: float"
				if parent:
					definition = f"node node_type_{i} from {parent}\n{fields}"
				else:
					definition = f"node node_type_{i}\n{fields}"
				eng.define_node(definition)

		self._run_benchmark(f"schema_define_node_types(nt: {n_types})", define_node_types)

		# Relation types
		def define_relation_types():
			eng = GraphiteEngine()
			# Predefine a few node types
			for i in range(min(n_types, 10)):
				eng.node_types[f"node_type_{i}"] = NodeType(f"node_type_{i}", [Field("x", DataType.INT)])
			for i in range(max(1, n_types // 2)):
				from_t = f"node_type_{i % 10}"
				to_t = f"node_type_{(i+1) % 10}"
				definition = f"relation Rel_{i}\n{from_t} -> {to_t}\nweight: float"
				eng.define_relation(definition)

		self._run_benchmark(
			f"schema_define_relation_types (rt: {max(1, n_types // 2)})",
			define_relation_types
		)

	# ---------- Node creation ----------
	def benchmark_node_creation(self):
		"""Create nodes in an already-defined engine."""
		# Build a tiny engine with schema to reuse
		engine = create_benchmark_engine(
			num_node_types=3,
			num_relation_types=1,
			num_nodes=0,
			num_relations=0
		)

		def create_many_nodes():
			# Create nodes of a specific type
			for i in range(self.size):
				engine.create_node("NodeType0", f"tmp_node_{i}",
					i, i*2+1, i*3, f"str_{i}", f"data_{i}",
					float(i)/10.0, "2023-01-01", True)

		def setup_clean():
			# Remove previously created nodes (but keep schema)
			for nid in list(engine.nodes.keys()):
				if nid.startswith("tmp_node_"):
					del engine.nodes[nid]
			engine.node_by_type["NodeType0"].clear()
			engine.relations.clear()
			gc.collect()

		self._run_benchmark(f"node_creation(n: {self.size})", create_many_nodes, _setup=setup_clean)

	# ---------- Relation creation ----------
	def benchmark_relation_creation(self):
		"""Benchmark creating relation instances"""
		engine = create_benchmark_engine(
			num_node_types=2, num_relation_types=1,
			num_nodes=self.size, num_relations=0
		)
		# Ensure nodes exist
		size = min(self.size, len(engine.nodes))

		def create_relations():
			for i in range(size):
				rel_type = next(iter(engine.relation_types))
				rel_type_obj = engine.relation_types[rel_type]
				# Just select valid node types
				src_n = next(iter(engine.node_by_type[rel_type_obj.from_type])).id
				tgt_n = next(iter(engine.node_by_type[rel_type_obj.to_type])).id
				engine.create_relation(src_n, tgt_n, rel_type, float(i)/100.0, f"edge_{i}")

		def setup_clean():
			engine.relations.clear()
			engine.relations_by_type.clear()
			engine.relations_by_from.clear()
			engine.relations_by_to.clear()
			gc.collect()

		self._run_benchmark(f"relation_creation(r: {size})", create_relations, _setup=setup_clean)

	# ---------- Queries ----------
	def benchmark_queries(self):
		"""Benchmark queries and related functions"""
		# Build a sufficiently large engine
		size = max(100, self.size)
		engine = create_benchmark_engine(
			num_node_types=4,
			num_relation_types=3,
			num_nodes=size,
			num_relations=size // 2
		)

		query = QueryBuilder(engine)
		all_nodes_result = query.all()

		# 1) get_node
		sample_id = "node_0"
		self._run_benchmark(f"get_node(n: {self.size})", engine.get_node, sample_id)

		# 2) get_nodes_of_type (with subtypes)
		self._run_benchmark(
			f"get_nodes_of_type(n: {self.size}, with subtypes)",
			engine.get_nodes_of_type,
			"NodeType0",
			True
		)

		# 3) get_relations_from / to
		sample_node = engine.nodes[f"node_{size//2}"]
		self._run_benchmark(
			f"query_get_relations_from(n: {self.size})",
			engine.get_relations_from,
			sample_node.id
		)
		self._run_benchmark(
			f"query_get_relations_to(n: {self.size})",
			engine.get_relations_to,
			sample_node.id
		)

		# 4) where (string condition)
		self._run_benchmark(
			f"query_where_string(n: {self.size})",
			lambda: all_nodes_result.where("int_field_0 > 500")
		)

		# 5) where (lambda)
		self._run_benchmark(
			f"query_where_lambda(n: {self.size})",
			lambda: all_nodes_result.where(lambda n: n.get("int_field_0") > 500)
		)

		# 6) traverse (outgoing)
		self._run_benchmark(
			f"query_outgoing(n: {self.size}, typed)",
			lambda: all_nodes_result.outgoing("RelType0")
		)

		# 7) aggregation: count, sum, avg, min, max, group_by, order_by
		limited = all_nodes_result.limit(100)
		self._run_benchmark("query_count(n: 100)", limited.count)
		self._run_benchmark("query_sum(n: 100)", limited.sum, "int_field_0")
		self._run_benchmark("query_avg(n: 100)", limited.avg, "float_field")
		self._run_benchmark("query_min(n: 100)", limited.min, "int_field_1")
		self._run_benchmark("query_max(n: 100)", limited.max, "int_field_1")
		self._run_benchmark("query_group_by(n: 100)", limited.group_by, "bool_field")
		self._run_benchmark("query_order_by(n: 100)", lambda: limited.order_by("int_field_0", True))

		# 8) set operation
		other = query.all().where("int_field_0 < 200")
		other_size = other.count()
		self._run_benchmark(f"query_union(n: 100 + {other_size})", lambda: limited.union(other))
		self._run_benchmark(f"query_exclude(n: 100 + {other_size})", lambda: limited.exclude(other))
		self._run_benchmark(f"query_intersect(n: 100 + {other_size})", lambda: limited.intersect(other))

		# 9) mutation: set
		self._run_benchmark("query_set(n: 100)", limited.set_val, int_field_0=9999)

		# 10) remove
		remove_result = limited
		self._run_benchmark("query_remove_node(n: 100)", remove_result.remove)

	# ---------- Serialization ----------
	def benchmark_serialization(self):
		"""Benchmark save / load engine"""
		size = max(100, self.size)
		engine = create_benchmark_engine(
			num_node_types=3,
			num_relation_types=2,
			num_nodes=size,
			num_relations=size // 2
		)
		filename = "_benchmark_temp.json"

		# Save
		self._run_benchmark(f"serialization_save(n: {size}, r: {size // 2})", engine.save, filename)

		# Load (safe)
		def load_safe():
			eng = GraphiteEngine()
			eng.load_safe(filename, max_size_mb=500, validate_schema=False)
			return eng

		self._run_benchmark(f"serialization_load(n: {size}, r: {size // 2}, validate off)", load_safe)

		# Load (safe + validation)
		def load_safe_validate():
			eng = GraphiteEngine()
			eng.load_safe(filename, max_size_mb=500, validate_schema=True)
			return eng

		self._run_benchmark(
			f"serialization_load(n: {size}, r: {size // 2}, validate on)", load_safe_validate
		)

		# Load (unsafe/low-level)
		def load_unsafe():
			eng = GraphiteEngine()
			eng.load(filename, safe_mode=False)
			return eng

		self._run_benchmark(f"serialization_load(n: {size}, r: {size // 2}, unsafe mode)", load_unsafe)

		# Cleanup
		try:
			os.remove(filename)
		except OSError:
			pass

	# ---------- DSL Parsing ----------
	def benchmark_dsl_parsing(self):
		"""Benchmark parsing DSL"""
		size = max(50, self.size // 10)
		# Generate DSL text with node/relation definitions and instances
		# definitions
		dsl_lines = [
			"node NodeA\nint_field: int\nstr_field: string\n",
			"node NodeB\nfloat_field: float\n",
			"relation REL_A\nNodeA -> NodeB\nweight: float\n",
		]

		# instances
		for i in range(1, size // 2, 2):
			dsl_lines.append(f"NodeA, node_{i}, {i}, \"example\"")
			dsl_lines.append(f"NodeB, node_{i+1}, {i}.5")
		for i in range(1, size // 2, 2):
			src_n = f"node_{i}"
			tgt_n = f"node_{i+1}"
			dsl_lines.append(f"{src_n} -[REL_A, {i/100.0}]-> {tgt_n}")

		dsl_text = "\n".join(dsl_lines)

		def parse_dsl():
			engine = GraphiteEngine()
			engine.parse(dsl_text)

		self._run_benchmark(f"dsl_parse({len(dsl_lines)} lines)", parse_dsl)

	# ---------- Memory ----------
	def benchmark_memory(self):
		"""Benchmark memory usage"""
		size = max(100, self.size)
		engine = create_benchmark_engine(
			num_node_types=3,
			num_relation_types=2,
			num_nodes=size,
			num_relations=size // 2
		)
		engine_size = asizeof.asizeof(engine)
		if engine:
			engine = None
		self.results[f"memory_overhead(n: {size}, r: {size // 2})"] = {
			"size_bytes": engine_size,
			"size_human": human_bytes(engine_size),
			"per_node_byte": engine_size / size if size else 0,
		}

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(bench: GraphiteBenchmarks, fmt: str = "plain") -> str:
	"""Format benchmark results as a string."""
	lines = []
	width = 60
	lines.append("=" * width)
	lines.append("GRAPHITE BENCHMARK REPORT")
	lines.append(f"Size factor: {bench.size}, Runs: {bench.runs}")
	lines.append("=" * width)

	if fmt == "json":
		return json.dumps(bench.results, indent=2, default=str)

	for name, stats in sorted(bench.results.items()):
		if isinstance(stats, dict) and "mean" in stats:
			mean_s = stats["mean"]
			mean_ms = mean_s * 1000
			lines.append(
				f"{name:<50} {mean_ms:8.3f} ms  (min:{stats['min']*1000:8.3f} ms, "
				f"max:{stats['max']*1000:8.3f} ms, stdev:{stats['stdev']*1000:8.3f} ms)"
			)
		elif isinstance(stats, dict) and "size_bytes" in stats:
			lines.append(
				f"{name:<50} {stats['size_human']:>11}  ({stats['size_bytes']} B, per node: "
				f"{stats['per_node_byte']} B)"
			)
		else:
			# Memory or other info
			lines.append(f"{name}: {stats}")

	lines.append("=" * width)
	return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main():
	"""Main entry point"""
	parser = argparse.ArgumentParser(
		description="Advanced benchmark suite for Graphite embedded graph database"
	)
	parser.add_argument(
		"--size", type=int, default=5000,
		help="Base number of elements to generate (nodes, relations). Default: 5000"
	)
	parser.add_argument(
		"--runs", type=int, default=10,
		help="Number of iterations for each micro-benchmark. Default: 10"
	)
	parser.add_argument(
		"--output", choices=["plain", "json"], default="plain",
		help="Report format. Default: plain"
	)
	args = parser.parse_args()

	print(f"Running Graphite benchmarks with size={args.size}, runs={args.runs} ...")
	bench = GraphiteBenchmarks(size=args.size, runs=args.runs)
	bench.benchmark_all()
	report = generate_report(bench, fmt=args.output)
	print(report)


if __name__ == "__main__":
	main()
