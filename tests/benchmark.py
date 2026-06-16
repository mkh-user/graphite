"""
Advanced benchmark suite for the Graphite embedded graph database.

Usage:
    python benchmark.py [--size N] [--runs M] [--output json|plain]

This script measures the performance of core Graphite operations under
synthetic, configurable workloads. It reports timing statistics and, where
possible, memory usage.
"""

import gc
import json
import os
import statistics
import sys
import time
from datetime import date
from typing import Any
from typing import Annotated

try:
	from pympler import asizeof
	import typer
	from tqdm import tqdm, trange
except ImportError as e:
	raise ImportError("Run 'pip install pympler typer tqdm)") from e

# ---------------------------------------------------------------------------
# Try to import graphite – if it isn't editable, use installed
# ---------------------------------------------------------------------------
try:
	# Add parent directory to path (assumes benchmark is inside the package or next to it)
	sys.path.insert(0, os.path.abspath('..'))
	from src.graphite import DataType, Field, NodeType, GraphiteEngine
	print("Source of Graphite found, using latest dev version")
except ImportError:
	print("Using installed Graphite version...")
	from graphite import DataType, Field, NodeType, GraphiteEngine

# ---------------------------------------------------------------------------
# Benchmark helpers
# ---------------------------------------------------------------------------
def timed_call(func, *args, _iterations: int, _setup=None, **kwargs) -> dict[str, float]:
	"""
	Time a callable over multiple iterations and return summary statistics.
	Runs garbage collection before each iteration to reduce noise.
	"""
	times = []
	for _ in trange(_iterations, desc=f"Running {func.__name__}", leave=False):
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


def n(num: float) -> str:
	"""Convert number to a human-readable string."""
	if num >= 1000000.0:
		return f"{num / 1000000.0:.1f}M"
	if num >= 1000.0:
		return f"{num / 1000.0:.1f}K"
	return str(num)


# ---------------------------------------------------------------------------
# Data generation for benchmarks
# ---------------------------------------------------------------------------
# pylint: disable=too-many-locals
def create_benchmark_engine(
	num_node_types: int,
	num_relation_types: int,
	num_nodes: int,
	num_relations: int,
	inheritance_depth: int,
) -> GraphiteEngine:
	"""
	Build an engine with a synthetic schema and populate it with nodes and relations.
	Returns the populated engine.
	"""
	engine = GraphiteEngine()

	# Define node types with a simple inheritance chain
	t = tqdm(total=4, desc="Creating benchmark engine", leave=False)
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
	t.update()

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
	t.update()

	# Populate nodes
	for node in range(num_nodes):
		type_idx = node % num_node_types
		node_id = f"node_{node}"
		# Generate some consistent 'random' values
		int_vals = [(node * 31 + j) % 1000 for j in range(3)]
		str_vals = [f"str_{node}_{j}" for j in range(2)]
		float_val = float(node % 100) / 10.0
		# Date as days from 2020-01-01
		date_val = date.fromordinal(date(2020, 1, 1).toordinal() + node % 10000)
		bool_val = node % 2 == 0

		values: dict[str, Any] = {
			f"int_field_{j}": int_vals[j] for j in range(3)
		}
		values.update({
			f"str_field_{j}": str_vals[j] for j in range(2)
		})
		values["float_field"] = float_val
		values["date_field"] = date_val
		values["bool_field"] = bool_val

		engine.create_node(f"NodeType{type_idx}", node_id, *values.values())
	t.update()

	# Populate relations
	for r in range(num_relations):
		rel_type_idx = r % num_relation_types
		rel_type_name = f"RelType{rel_type_idx}"
		rel_type_obj = engine.relation_types[rel_type_name]
		from_id = next(iter(engine.node_by_type[rel_type_obj.from_type]))
		to_id = next(iter(engine.node_by_type[rel_type_obj.to_type]))
		values = {"weight": float(r % 100) / 100.0, "label": f"edge_{r}"}
		engine.create_relation(from_id, to_id, rel_type_name, *values.values())
	t.update()
	t.close()
	return engine


# ---------------------------------------------------------------------------
# Benchmark class
# ---------------------------------------------------------------------------
class GraphiteBenchmarks: # pylint: disable=too-many-instance-attributes
	"""Collection of micro-benchmarks for Graphite."""

	# pylint: disable=too-many-arguments, too-many-positional-arguments
	def __init__(
		self,
		size: int,
		runs: int,
		node_types: int,
		relation_types: int,
		relations_ratio: float,
		inheritance_depth: int,
	):
		self.size = size
		self.hsize = n(size)
		self.runs = runs
		self.node_types = node_types
		self.relation_types = relation_types
		self.relations_ratio = relations_ratio
		self.relations_count = int(size * relations_ratio)
		self.inheritance_depth = inheritance_depth
		self.results: dict[str, Any] = {}

	def _run_benchmark(self, name: str, func, *args, _setup=None, **kwargs):
		"""Execute a timed call and store the result."""
		stats = timed_call(func, *args, _iterations=self.runs, _setup=_setup, **kwargs)
		self.results[name] = stats
		return stats

	def create_default_engine(self):
		"""Create an engine with default size."""
		return create_benchmark_engine(
			self.node_types,
			self.relation_types,
			self.size,
			self.relations_count,
			self.inheritance_depth,
		)

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
		n_types = self.node_types

		t = tqdm(total=2, desc="Benchmark: Schema", leave=False)

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

		self._run_benchmark(f"schema_define_node_types(nt: {n(n_types)})", define_node_types)
		t.update()

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
			f"schema_define_relation_types (rt: {n(max(1, n_types // 2))})",
			define_relation_types
		)
		t.update()
		t.close()

	# ---------- Node creation ----------
	def benchmark_node_creation(self):
		"""Create nodes in an already-defined engine."""
		# Build a tiny engine with schema to reuse
		engine = create_benchmark_engine(
			self.node_types, self.relation_types, 0, 0, 1
		)

		t = tqdm(total=1, desc="Benchmark: Node Creation", leave=False)

		def create_many_nodes():
			# Create nodes of a specific type
			for i in trange(self.size, desc="Creating nodes", leave=False):
				engine.create_node("NodeType0", f"tmp_node_{i}",
					i, i*2+1, i*3, f"str_{i}", f"data_{i}",
					float(i)/10.0, date(2023, 1, 1), True)

		def setup_clean():
			# Remove previously created nodes (but keep schema)
			for nid in list(engine.nodes.keys()):
				if nid.startswith("tmp_node_"):
					del engine.nodes[nid]
			engine.node_by_type["NodeType0"].clear()
			engine.relations.clear()
			gc.collect()

		self._run_benchmark(f"node_creation(n: {n(self.size)})", create_many_nodes, _setup=setup_clean)
		t.close()

	# ---------- Relation creation ----------
	def benchmark_relation_creation(self):
		"""Benchmark creating relation instances"""
		engine = create_benchmark_engine(
			self.node_types, self.relation_types, self.size, 0, 1
		)

		t = tqdm(total=2, desc="Benchmark: Relation Creation", leave=False)

		def create_relations():
			for i in trange(self.size, desc="Creating relations", leave=False):
				rel_type = next(iter(engine.relation_types))
				rel_type_obj = engine.relation_types[rel_type]
				# Just select valid node types
				src_n = next(iter(engine.node_by_type[rel_type_obj.from_type]))
				tgt_n = next(iter(engine.node_by_type[rel_type_obj.to_type]))
				engine.create_relation(src_n, tgt_n, rel_type, float(i)/100.0, f"edge_{i}")

		def setup_clean():
			engine.remove_relations(set(engine.relations.values()))
			gc.collect()

		self._run_benchmark(f"relation_creation(r: {n(self.size)})", create_relations, _setup=setup_clean)
		t.close()

	# ---------- Queries ----------
	def benchmark_queries(self):
		"""Benchmark queries and related functions"""
		t = tqdm(total=22, desc="Benchmark: Queries", leave=False)

		engine = self.create_default_engine()
		query = engine.query
		all_nodes_result = query.all()
		limited = all_nodes_result.limit(100)
		remove_result = all_nodes_result.limit(100)
		other = query.all().where("int_field_0 < 200")
		other_operation_size = n(limited.union(other).count())

		def query_where_string():
			all_nodes_result.where("int_field_0 > 500")

		def query_where_lambda():
			all_nodes_result.where(lambda node: node.get("int_field_0") > 500)

		def query_outgoing():
			all_nodes_result.outgoing("RelType0")

		def query_incoming():
			all_nodes_result.incoming("RelType0")

		def query_both():
			all_nodes_result.both("RelType0")

		benchmarks = [
			(
				f"get_node(n: {self.hsize})", engine.get_node,
				"node_0"
			), (
				f"get_nodes_of_type(n: {n(self.size)}, with subtypes)", engine.get_nodes_of_type,
				"NodeType0", True
			), (
				f"query_get_relations_from(n: {n(self.size)})", engine.get_relations_from,
				f"node_{self.size//2}"
			), (
				f"query_get_relations_to(n: {n(self.size)})", engine.get_relations_to,
				f"node_{self.size//2}"
			), (
				f"query_where_string(n: {n(self.size)})", query_where_string
			), (
				f"query_where_lambda(n: {n(self.size)})", query_where_lambda
			), (
				f"query_outgoing(n: {n(self.size)}, typed)", query_outgoing
			), (
				f"query_incoming(n: {n(self.size)}, typed)", query_incoming
			), (
				f"query_both(n: {n(self.size)}, typed)", query_both
			), (
				"query_count(n: 100)", limited.count
			), (
				"query_sum(n: 100)", limited.sum,
				"int_field_0"
			), (
				"query_avg(n: 100)", limited.avg,
				"float_field"
			), (
				"query_min(n: 100)", limited.min,
				"int_field_1"
			), (
				"query_max(n: 100)", limited.max,
				"int_field_1"
			), (
				"query_group_by(n: 100)", limited.group_by,
				"bool_field"
			), (
				"query_order_by(n: 100)", limited.order_by,
				"int_field_0", True
			), (
				f"query_union(n: {other_operation_size})", limited.union,
				other
			), (
				f"query_exclude(n: {other_operation_size})", limited.exclude,
				other
			), (
				f"query_intersect(n: {other_operation_size})", limited.intersect,
				other
			), (
				"query_remove_node(n: 100)", remove_result.remove,
			), (
				f"query_validate(n: {n(other.count())})", other.validate
			)
		]

		for b in benchmarks:
			if len(b) < 2:
				raise ValueError(f"Invalid benchmark configuration {b}")
			if len(b) == 2:
				self._run_benchmark(b[0], b[1])
			else:
				self._run_benchmark(b[0], b[1], *b[2:])
			t.update()

		self._run_benchmark("query_set(n: 100)", limited.set_val, int_field_0=9999)
		t.update()
		t.close()

	# ---------- Serialization ----------
	def benchmark_serialization(self):
		"""Benchmark save / load engine"""
		engine = self.create_default_engine()
		filename = "_benchmark_temp.json"

		t = tqdm(total=4, desc="Benchmark: Serialization", leave=False)

		# Save
		self._run_benchmark(
			f"serialization_save(n: {self.hsize}, r: {n(self.relations_count)})",
			engine.save,
			filename
		)
		t.update()

		# Load (safe)
		def load_safe():
			eng = GraphiteEngine()
			eng.load_safe(filename, max_size_mb=500, validate_schema=False)
			return eng

		self._run_benchmark(
			f"serialization_load(n: {self.hsize}, r: {n(self.relations_count)}, validate off)",
			load_safe
		)
		t.update()

		# Load (safe + validation)
		def load_safe_validate():
			eng = GraphiteEngine()
			eng.load_safe(filename, max_size_mb=500, validate_schema=True)
			return eng

		self._run_benchmark(
			f"serialization_load(n: {self.hsize}, r: {n(self.relations_count)}, validate on)",
			load_safe_validate
		)
		t.update()

		# Load (unsafe/low-level)
		def load_unsafe():
			eng = GraphiteEngine()
			eng.load(filename, safe_mode=False)
			return eng

		self._run_benchmark(
			f"serialization_load(n: {self.hsize}, r: {n(self.relations_count)}, unsafe mode)",
			load_unsafe
		)
		t.update()
		t.close()

		# Cleanup
		try:
			os.remove(filename)
		except OSError:
			pass

	# ---------- DSL Parsing ----------
	def benchmark_dsl_parsing(self):
		"""Benchmark parsing DSL"""
		size = max(50, self.size // 10)

		t = tqdm(total=1, desc="Benchmark: DSL Parsing", leave=False)

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
		t.update()
		t.close()

	# ---------- Memory ----------
	def benchmark_memory(self):
		"""Benchmark memory usage"""
		size = max(100, self.size)
		t = tqdm(total=1, desc="Benchmark: Memory", leave=False)
		engine = self.create_default_engine()
		engine_size = asizeof.asizeof(engine)
		if engine:
			engine = None
		self.results[f"memory_overhead(n: {n(size)}, r: {n(size // 2)})"] = {
			"size_bytes": engine_size,
			"size_human": human_bytes(engine_size),
			"per_node_byte": int(round(engine_size / size if size else 0)),
		}
		t.update()
		t.close()

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(bench: GraphiteBenchmarks, dump_json: bool = False) -> str:
	"""Format benchmark results as a string."""
	if dump_json:
		return json.dumps(bench.results, indent=2, default=str)

	lines: list = []
	width = 115
	lines.append("=" * width)
	lines.append(" " * 45 + "GRAPHITE BENCHMARK REPORT")
	lines.append(" " * 45 + f"Size factor: {n(bench.size)}, Runs: {bench.runs}")
	lines.append("=" * width)
	lines.append("| Metric " + " " * 49 + "| Avg         | Min         | Max         | StDev       |")
	lines.append("|" + "-" * 57 + "|" + ("-" * 13 + "|") * 4)

	memory_info = None
	for name, stats in sorted(bench.results.items()):
		if isinstance(stats, dict) and "mean" in stats:
			mean_s = stats["mean"]
			mean_ms = mean_s * 1000
			lines.append(
				f"| {name:<55} | {mean_ms:8.3f} ms | {stats['min']*1000:8.3f} ms | "
				f"{stats['max']*1000:8.3f} ms | {stats['stdev']*1000:8.3f} ms |"
			)
		elif isinstance(stats, dict) and "size_bytes" in stats:
			memory_info = (
				f"Memory overhead: {stats['size_human']} (total: {stats['size_bytes']} B, "
				f"per node: {stats['per_node_byte']} B)"
			)
		else:
			# Other info
			lines.append(f"| {name:<50} | {stats} |")
	if memory_info:
		if len(lines) == 6:
			lines.clear()
		lines.append(memory_info)
	if len(lines) == 6:
		return "No benchmark to report."

	return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
# pylint: disable=too-many-arguments, too-many-positional-arguments, unused-argument
def main(
	size: Annotated[int, typer.Option(help="Database size (nodes)")] = 100000,
	runs: Annotated[int, typer.Option(help="Runs to benchmark")] = 10,
	node_types: Annotated[int, typer.Option(help="Number of node types")] = 5,
	relation_types: Annotated[int, typer.Option(help="Number of relation types")] = 3,
	relations_ratio: Annotated[float, typer.Option(help="Relation ratio")] = 0.5,
	inheritance_depth: Annotated[int, typer.Option(help="Inheritance depth on node types")] = 1,
	dump_json: Annotated[
		bool,
		typer.Option("--json", help="Output to JSON instead of table")
	] = False,
	run_all: Annotated[bool, typer.Option(help="Run all benchmarks")] = True,
	on_schema: Annotated[
		bool,
		typer.Option(help="Benchmark node type and relation type definitions")
	] = None, # ty: ignore[invalid-parameter-default]
	on_node_creation: Annotated[
		bool,
		typer.Option(help="Benchmark node creation")
	] = None, # ty: ignore[invalid-parameter-default]
	on_relation_creation: Annotated[
		bool,
		typer.Option(help="Benchmark relation creation")
	] = None, # ty: ignore[invalid-parameter-default]
	on_queries: Annotated[
		bool,
		typer.Option(help="Benchmark queries")
	] = None, # ty: ignore[invalid-parameter-default]
	on_serialization: Annotated[
		bool,
		typer.Option(help="Benchmark save and load")
	] = None, # ty: ignore[invalid-parameter-default]
	on_dsl_parse: Annotated[
		bool,
		typer.Option(help="Benchmark a complete DSL parsing")
	] = None, # ty: ignore[invalid-parameter-default]
	on_memory: Annotated[
		bool,
		typer.Option(help="Benchmark memory usage")
	] = None, # ty: ignore[invalid-parameter-default]
):
	"""
	Advanced benchmark suite for Graphite embedded graph database
	"""
	bench = GraphiteBenchmarks(
		size,
		runs,
		node_types,
		relation_types,
		relations_ratio,
		inheritance_depth,
	)

	benchmarks = {
		"on_schema": bench.benchmark_schema_definition,
		"on_node_creation": bench.benchmark_node_creation,
		"on_relation_creation": bench.benchmark_relation_creation,
		"on_queries": bench.benchmark_queries,
		"on_serialization": bench.benchmark_serialization,
		"on_dsl_parse": bench.benchmark_dsl_parsing,
		"on_memory": bench.benchmark_memory
	}

	benchmarks_to_run = {
		name: func
		for name, func in benchmarks.items()
		if (run_all and (locals()[name] is None or locals()[name])) or (not run_all and locals()[name])
	}

	n_benchmarks = len(benchmarks_to_run)
	if n_benchmarks:
		print(
			f"Running {n_benchmarks} benchmarks: " + ", ".join(benchmarks_to_run.keys())
		)
		for _, func in tqdm(benchmarks_to_run.items(), desc="Running benchmarks"):
			func()

	report = generate_report(
		bench,
		dump_json
	)
	print(report)


if __name__ == "__main__":
	typer.run(main)
