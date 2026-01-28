from errors import GError

class QueryExecutor:
	def __init__(self, nodes: dict[str, dict], relations: dict[str, dict]) -> None:
		self.nodes = nodes
		self.relations = relations

	def execute(self, ast: dict) -> set | dict:
		current = {
			nid for nid, n in self.nodes.items()
			if n["meta"]["type"] == ast["start"]
		}
		for step in ast["steps"]:
			t = step["type"]
			if t == "traverse":
				current = self.traverse(
					current,
					step["relation"],
					step["mode"]
				)
			elif t == "where":
				current = self.filter_nodes(
					current,
					step["field"],
					step["op"],
					step["value"]
				)
			elif t == "where_rel":
				current = self.filter_relations(
					current,
					step["rtype"],
					step["field"],
					step["op"],
					step["value"]
				)
			elif t == "select":
				current = self.select(
					current,
					step["fields"],
				)
			elif t == "order_by":
				current = self.order_by(
					current,
					step["fields"]
				)
			elif t == "offset":
				current = self.offset(
					current,
					step["value"]
				)
			elif t == "limit":
				current = self.limit(
					current,
					step["value"]
				)
		return current

	def traverse(self, node_ids: set, relation_type: str, mode: str = "via") -> set:
		result = set()
		for r in self.relations.values():
			meta = r["meta"]
			if meta["type"] != relation_type:
				continue
			frm = meta["from"]
			to = meta["to"]
			if mode in ("out", "via") and frm in node_ids:
				result.add(to)
			if mode in ("in", "via") and to in node_ids:
				result.add(frm)
		return result

	def filter_nodes(self, node_ids: set, field: str, op: str, value) -> set:
		return {
			nid for nid in node_ids
			if field in self.nodes[nid]["properties"]
			and self._cmp(self.nodes[nid]["properties"][field], op, value)
		}

	def filter_relations(self, node_ids: set, relation_type: str, field: str, op: str, value) -> set:
		result = set()
		for r in self.relations.values():
			meta = r["meta"]
			props = r["properties"]
			if meta["type"] != relation_type:
				continue
			if field not in props:
				continue
			if not self._cmp(props[field], op, value):
				continue
			if meta["from"] in node_ids:
				result.add(meta["to"])
			if meta["to"] in node_ids:
				result.add(meta["from"])
		return result

	def select(self, node_ids: set, fields: list[str]) -> dict:
		result = {}
		for nid in node_ids:
			node = self.nodes[nid]
			row = {}
			for f in fields:
				if f in node["properties"]:
					row[f] = node["properties"][f]
			if row:
				result[nid] = row
		return result

	@staticmethod
	def limit(rows: dict, n: int) -> dict:
		if n < 0:
			return rows
		return dict(list(rows.items())[:n])

	@staticmethod
	def offset(rows: dict, n: int) -> dict:
		if n <= 0:
			return rows
		return dict(list(rows.items())[n:])

	@staticmethod
	def order_by(rows: dict, fields: list[tuple[str, str]]) -> dict:
		items = list(rows.items())

		for field, direction in reversed(fields):
			items.sort(
				key=lambda item: item[1].get(field),
				reverse=(direction == "desc")
			)

		return dict(items)

	@staticmethod
	def _cmp(a, op, b):
		return (
			a > b if op == ">"
			else a == b if op == "=="
			else a < b if op == "<"
			else False
		)

	@staticmethod
	def parse_query(q: str) -> GError | dict:
		tokens = _tokenize(q)
		ast = {
			"start": tokens[0],
			"steps": []
		}
		i = 1
		while i < len(tokens):
			if tokens[i] != ".":
				return GError(f"Expected '.', got {tokens[i]}")
			i += 1
			step = tokens[i]
			i += 1
			if step in ("via", "in", "out"):
				if tokens[i] != "(":
					return GError(f"Expected '(', got {tokens[i]}")
				i += 1
				rel = tokens[i]
				i += 1
				if tokens[i] != ")":
					return GError(f"Expected ')', got {tokens[i]}")
				i += 1
				ast["steps"].append(
					{
						"type"    : "traverse",
						"mode"    : step,
						"relation": rel
					}
				)
			elif step in ("where", "where_rel"):
				if tokens[i] != "(":
					return GError(f"Expected '(', got {tokens[i]}")
				i += 1
				rtype: str = ""
				if step == "where_rel":
					rtype = tokens[i]
					i += 1
					if tokens[i] != ",":
						return GError(f"Expected ',', got {tokens[i]}")
					i += 1
				field = tokens[i]
				op = tokens[i + 1]
				value = _parse_str(tokens[i + 2])[0]
				i += 3
				if tokens[i] != ")":
					return GError(f"Expected ')', got {tokens[i]}")
				i += 1
				if step == "where":
					ast["steps"].append(
						{
							"type" : step,
							"field": field,
							"op"   : op,
							"value": value
						}
					)
				elif step == "where_rel":
					ast["steps"].append(
						{
							"type" : step,
							"rtype": rtype,
							"field": field,
							"op"   : op,
							"value": value
						}
					)
			elif step == "select":
				if tokens[i] != "(":
					return GError(f"Expected '(', got {tokens[i]}")
				i += 1
				fields = []
				while tokens[i] != ")":
					if tokens[i] != ",":
						fields.append(tokens[i])
					i += 1
				i += 1
				ast["steps"].append({
					"type" : "select",
					"fields": fields,
				})
			elif step == "order_by":
				if tokens[i] != "(":
					return GError(f"Expected '(', got {tokens[i]}")
				i += 1
				fields = []
				while tokens[i] != ")":
					name = tokens[i]
					direction = "asc"
					if tokens[i + 1] in ("asc", "desc"):
						direction = tokens[i + 1]
						i += 1
					fields.append((name, direction))
					i += 1
					if tokens[i] == ",":
						i += 1
				i += 1
				ast["steps"].append({
					"type" : "order_by",
					"fields": fields,
				})
			elif step in ("offset", "limit"):
				if tokens[i] != "(":
					return GError(f"Expected '(', got {tokens[i]}")
				i += 1
				value = _parse_str(tokens[i])[0]
				i += 1
				if tokens[i] != ")":
					return GError(f"Expected ')', got {tokens[i]}")
				i += 1
				ast["steps"].append({
					"type" : step,
					"value": value,
				})
			else:
				return GError(f"Unknown step: {step}")
		return ast

class GraphiteDb:
	"""
	A Graphite database object in pure Python.

	Usual setup workflow: Create database -> Import structure -> Import data
	"""

	def __init__(self):
		self.struct = {}
		self.nodes = {}
		self.relations = {}
		self.current_block: dict = {}
		self.NODE_DEFINE = "node"
		self.BT_NODE_DEFINE = "node_define"
		self.RELATION_DEFINE = "relation"
		self.BT_RELATION_DEFINE = "relation_define"

	def parse_struct(self, code: str) -> GError | None:
		"""
		Parses a struct code into database, supports multiple runs in one database to expand current structure.

		**Note:** This function returns a GError if the structure is invalid, in this situation you need to create a new database object to ensure it is valid.

		:param code: ``str`` in ``.gdbs`` syntax
		:return: ``GError`` as error or ``None``
		"""
		last_line_was_relation_define = False
		reach_relation_define_dash = False
		for line in code.splitlines():
			this_line_was_relation_define = False
			if not line.strip():
				continue
			tokens = _tokenize(line.strip())
			index = 0
			for t in tokens:
				is_last = index == len(tokens) - 1
				if t == self.NODE_DEFINE:
					if self.current_block:
						err = self._close_block(self.current_block)
						if err:
							return err
					self.current_block = {
						"meta": {
							"type": self.BT_NODE_DEFINE,
							"flags": [],
							"properties_order": [],
						},
						"properties": {}
					}
				elif t == self.RELATION_DEFINE:
					if self.current_block:
						err = self._close_block(self.current_block)
						if err:
							return err
					self.current_block = {
						"meta": {
							"type": self.BT_RELATION_DEFINE,
							"from": [],
							"to": [],
							"flags": [],
							"reverse": "",
							"properties_order": [],
						},
						"properties": {},
					}
					reach_relation_define_dash = False
				elif self.current_block and self.current_block["meta"]["type"] == self.BT_NODE_DEFINE:
					if tokens[index - 1] == self.NODE_DEFINE:
						self.current_block["meta"]["name"] = t
					elif t == "from":
						pass # 'from' will be handled in next iteration in this situation.
					elif tokens[index - 1] == "from":
						self.current_block["meta"]["from"] = t
					elif not is_last and tokens[index + 1] == ":":
						pass # This is a property, will be handled when parse reach its type.
					elif t == ":":
						pass
					elif tokens[index - 1] == ":":
						if _is_type_valid(t):
							if tokens[index - 2] in self.current_block["properties"].keys():
								return GError(
									f"Parameter {tokens[index - 2]} is already defined for node {self.current_block["meta"]["name"]}"
								)
							self.current_block["properties"][tokens[index - 2]] = t
							self.current_block["meta"]["properties_order"].append(tokens[index - 2])
						else:
							return GError(
								f"Invalid type '{t}' for parameter '{tokens[index - 2]}' in node {self.current_block["meta"]["name"]}"
							)
					else:
						return GError(
							f"Invalid token in node definition block! Expected name, from, or property, got {t}"
						)
				elif self.current_block and self.current_block["meta"]["type"] == self.BT_RELATION_DEFINE:
					if tokens[index - 1] == self.RELATION_DEFINE:
						self.current_block["meta"]["name"] = t
					elif t == "both":
						self.current_block["meta"]["flags"].append("both")
					elif t == "reverse":
						pass # This relation has a reverse shadow, will be handle in next interation
					elif tokens[index - 1] == "reverse":
						self.current_block["meta"]["reverse"] = t
					elif last_line_was_relation_define:
						if t == ",": # Skip comma, this comma is just for readability and can be removed in code
							pass
						elif t == "-":
							reach_relation_define_dash = True
						elif not reach_relation_define_dash:
							self.current_block["meta"]["from"].append(t)
						else:
							self.current_block["meta"]["to"].append(t)
					elif not is_last and tokens[index + 1] == ":":
						pass # This is a property, will be handled when parse reach its type.
					elif t == ":":
						pass
					elif tokens[index - 1] == ":":
						if _is_type_valid(t):
							if tokens[index - 2] in self.current_block["properties"].keys():
								return GError(
									f"Parameter {tokens[index - 2]} is already defined for relation {self.current_block["meta"]["name"]}"
								)
							self.current_block["properties"][tokens[index - 2]] = t
							self.current_block["meta"]["properties_order"].append(tokens[index - 2])
						else:
							return GError(
								f"Invalid type '{t}' for parameter '{tokens[index - 2]}' in relation {self.current_block["meta"]["name"]}"
							)
					else:
						return GError(
							f"Invalid token in relation definition block! Expected name, both, reverse, from, to, or property, got {t}"
						)
				else:
					return GError(f"Invalid token: {t}")
				if t == self.RELATION_DEFINE:
					this_line_was_relation_define = True
				index += 1
			last_line_was_relation_define = this_line_was_relation_define
		if self.current_block:
			err = self._close_block(self.current_block)
			if err:
				return err
		return None

	def parse_data(self, data: str) -> GError | None:
		"""
		Parses a database code (usually ``.gdb`` file) to current database.

		:param data: ``str`` in ``.gdb`` syntax
		:return: ``GError`` as error or ``None``
		"""
		if not self.struct:
			return GError("Please parse structure before data")
		for line in data.splitlines():
			if not line.strip():
				continue
			tokens = _tokenize(line)
			if tokens[1] == ",":
				ntype = tokens.pop(0)
				if ntype == ",":
					return GError("Invalid syntax! Expected node type, got comma")
				if tokens.pop(0) != ",":
					return GError("Invalid syntax! Expected comma (',') after node type")
				nid = tokens.pop(0)
				if ntype == ",":
					return GError("Invalid syntax! Expected node id, got comma")
				if tokens.pop(0) != ",":
					return GError("Invalid syntax! Expected comma (',') after node id")
				properties = []
				while tokens:
					if tokens[0] == ",":
						tokens.pop(0)
						continue
					properties.append(_parse_str(tokens.pop(0))[0])
				err = self.add_node(ntype, nid, properties)
				if err:
					return err
				continue
			elif tokens[1] == "-" and tokens[2] == "[":
				source = tokens.pop(0)
				if source == ",":
					return GError("Invalid syntax! Expected source node, got comma")
				if "".join(tokens[0:2]) != "-[":
					return GError("Invalid syntax! Expected '-[' after source node")
				tokens.pop(0)
				tokens.pop(0)
				rtype = tokens.pop(0)
				if rtype == ",":
					return GError("Invalid syntax! Expected relation type, got comma")
				properties = []
				while tokens:
					if tokens[0] == ",":
						tokens.pop(0)
						continue
					if tokens[0] == "]":
						tokens.pop(0)
						break
					properties.append(_parse_str(tokens.pop(0))[0])
				if not tokens:
					return GError("Invalid syntax! Expected ']-' or ']>' after relation")
				if tokens.pop(0) not in ["-", ">"]:
					return GError("Invalid syntax! Expected '-' or '>' after relation")
				if not tokens:
					return GError("Invalid syntax! Missing target node")
				target = tokens.pop(0)
				if tokens:
					return GError(f"Invalid syntax! Expected end of line, got {tokens.pop(0)}")
				err = self.add_relation(rtype, source, target, properties)
				if err:
					return err
				continue
			else:
				return GError(f"Invalid syntax! Expected node ('..., ...') or relation ('... -[...') pattern")
		return None

	def query(self, q: str) -> set | GError:
		ast = self._safe_query(QueryExecutor.parse_query(q))
		if isinstance(ast, GError):
			return ast
		executor = QueryExecutor(self.nodes, self.relations)
		return executor.execute(ast)

	def _safe_query(self, ast: dict | GError) -> dict | GError:
		if isinstance(ast, GError):
			return ast
		if not self.has_node_type(ast["start"]):
			return GError(f"Invalid node type: {ast['start']}")
		for step in ast["steps"]:
			t = step["type"]
			if t not in ("traverse", "where", "where_rel", "select", "order_by", "limit", "offset"):
				return GError(f"Invalid step: {t}")
			if t == "traverse":
				if not self.has_relation_type(step["relation"]):
					return GError(f"Invalid relation type: {step['relation']}")
				if step["mode"] not in ("via", "in", "out"):
					return GError(f"Invalid traverse mode: {step['mode']}")
			elif t == "where":
				if step["op"] not in ("<", "==", ">"):
					return GError(f"Invalid operation: {step["op"]}")
			elif t == "where_rel":
				if not self.has_relation_type(step["rtype"]):
					return GError(f"Invalid relation type: {step['rtype']}")
				if step["op"] not in ("<", "==", ">"):
					return GError(f"Invalid operation: {step["op"]}")
		return ast

	def struct_overview(self, include_properties: bool = True) -> str:
		"""
		Returns a human-readable overview of the current database structure. This is useful for print and debug information.
		Overview is not limited to specific count of items, so this is a raw structure representation too.

		:param include_properties: If ``True``, include properties in the overview
		:return: A human-readable overview of the current database structure as string.
		"""
		overview = ""
		for item in self.struct.values():
			if item["meta"]["type"] == "node_define":
				overview += "Node "
			else:
				overview += "Relation "
			overview += item["meta"]["name"]
			if item["meta"]["type"] == "node_define" and "from" in item["meta"]:
				overview += f" ({item["meta"]["from"]})"
			if item["meta"]["type"] == "relation_define" and item["meta"]["reverse"]:
				overview += f" (reverse: {item["meta"]["reverse"]})"
			if item["meta"]["type"] == "relation_define" and "both" in item["meta"]["flags"]:
				overview += f" (both)"
			if item["meta"]["type"] == "relation_define":
				overview += f" <{", ".join(item['meta']['from'])} -> {", ".join(item['meta']['to'])}>"
			overview += "\n"
			if include_properties:
				if item["meta"]["type"] == "node_define" and "from" in item["meta"]:
					hidden = len(self._list_properties(item["meta"]["from"]))
				else:
					hidden = 0
				if hidden:
					overview += f"\t {hidden}\tfrom parent\n"
				for p in item["properties"]:
					overview += f"\t({item["meta"]["properties_order"].index(p) + hidden})\t{p}: {item["properties"][p]}\n"
		return overview

	def nodes_overview(self, include_properties: bool = True) -> str:
		"""
		Returns a human-readable overview of the current database nodes as string. This is useful for print and debug information.
		Overview is not limited to specific count of nodes, so this is a raw nodes representation too.

		:param include_properties: If ``True``, include properties in the overview
		:return: A human-readable overview of the current database nodes as string.
		"""
		overview = ""
		for item in self.nodes:
			overview += f"{self.nodes[item]["meta"]["type"]} {item}\n"
			if include_properties:
				for p in self.nodes[item]["properties"]:
					overview += f"\t{p}: {self.nodes[item]["properties"][p]}\n"
		return overview.strip()

	def relations_overview(self, include_properties: bool = True) -> str:
		"""
		Returns a human-readable overview of the current database relations as string. This is useful for print and debug information.
		Overview is not limited to specific count of relations, so this is a raw relations representation too.

		:param include_properties: If ``True``, include properties in the overview
		:return: A human-readable overview of the current database relations as string.
		"""
		overview = ""
		for item in self.relations:
			info = self.relations[item]
			overview += f"{info["meta"]["type"]}: {info["meta"]["from"]} -> {info["meta"]["to"]} <{info["meta"]["from_type"]} -> {info["meta"]["to_type"]}>"
			if "both" in self.struct["relation_" + info["meta"]["type"]]["meta"]["flags"]:
				overview += f" (both)"
			if self.struct["relation_" + info["meta"]["type"]]["meta"]["reverse"]:
				overview += f" (reverse: {self.struct["relation_" + info["meta"]["type"]]["meta"]["reverse"]})"
			overview += "\n"
			if include_properties:
				for p in info["properties"]:
					overview += f"\t{p}: {info["properties"][p]}\n"
		return overview.strip()

	def add_node(self, node_type: str, node_id: str, properties: list | dict) -> GError | None:
		"""
		Adds a new node to database. Node must be valid in parsed structure. This is a mid-level API and not implemented for direct use, use ``parse_data`` instead.

		**Note:** When ``node_id`` parameter is duplicate, node will be overwritten.

		:param node_type: Type of the node, from defined types in structure.
		:param node_id: A unique identifier for the node. This is the fastest access way to node without query and relations to this node need this ID.
		:param properties: A dictionary or list of node properties.
		:return: ``GError`` as error or ``None``
		"""
		if not self.has_node_type(node_type):
			return GError(f"Invalid node type '{node_type}'")
		type_properties = self._list_properties(node_type)
		new_node = {
			"meta"      : {
				"type": node_type,
			},
			"properties": {},
		}
		p = _load_properties("node", node_type, type_properties, properties)
		if isinstance(p, GError):
			return p
		new_node["properties"] = p
		self.nodes[node_id] = new_node
		return None

	def add_relation(self, relation_type: str, from_node: str, to_node: str, properties: list | dict) -> GError | None:
		"""
		Adds a new relation to database. Relation must be valid in parsed structure. This is a mid-level API and not implemented for direct use, use ``parse_data`` instead.

		**Note:** When a relation from same type as ``relation_type`` exists between ``from_node`` and ``to_node``, skips call and prints a warning.

		:param relation_type: Type of the relation, from defined types in structure.
		:param from_node: Source node
		:param to_node: Target node
		:param properties: A dictionary or list of relation properties.
		:return: ``GError`` as error or ``None``
		"""
		if f"{relation_type} {from_node} {to_node}" in self.relations:
			print(
				f"Graphite Warning: Relation '{relation_type}' from '{from_node}' to '{to_node}' already exists, skipping."
			)
			return None
		new_from = None
		new_to = None
		if not self.has_relation_type(relation_type):
			for r in self.struct.values():
				if r["meta"]["type"] == self.BT_RELATION_DEFINE:
					if r["meta"]["reverse"] == relation_type:
						relation_type = r["meta"]["name"]
						new_from = to_node
						new_to = from_node
						break
			if not (new_from and new_to):
				return GError(f"Invalid relation type '{relation_type}'")
		if new_from and new_to:
			from_node = new_from
			to_node = new_to
		if from_node not in self.nodes:
			return GError(f"Node '{from_node}' does not exist")
		if to_node not in self.nodes:
			return GError(f"Node '{to_node}' does not exist")
		from_type = self.nodes[from_node]["meta"]["type"]
		to_type = self.nodes[to_node]["meta"]["type"]
		if not self.is_relation_valid(relation_type, from_type, to_type):
			return GError(
				f"Relation type '{relation_type}' is not valid from '{from_node}' ({from_type}) to '{to_node}' ({to_type})"
			)
		type_properties = self._list_relation_properties(relation_type)
		new_relation = {
			"meta"      : {
				"type"     : relation_type,
				"from"     : from_node,
				"to"       : to_node,
				"from_type": from_type,
				"to_type"  : to_type,
			},
			"properties": {},
		}
		p = _load_properties("relation", relation_type, type_properties, properties)
		if isinstance(p, GError):
			return p
		new_relation["properties"] = p
		self.relations[f"{relation_type} {from_node} {to_node}"] = new_relation

	def _list_relation_properties(self, relation_type: str) -> dict[str, str]:
		properties: dict[str, str] = {}
		if self.has_relation_type(relation_type):
			for p in self.struct["relation_" + relation_type]["properties"]:
				properties[p] = self.struct["relation_" + relation_type]["properties"][p]
		return properties

	def _list_properties(self, node_type: str) -> dict[str, str]:
		properties: dict[str, str] = {}
		if self.has_node_type(node_type):
			if "from" in self.struct["node_" + node_type]["meta"]:
				properties = self._list_properties(self.struct["node_" + node_type]["meta"]["from"])
			for p in self.struct["node_" + node_type]["properties"]:
				properties[p] = self.struct["node_" + node_type]["properties"][p]
		return properties

	def _close_block(self, block: dict) -> GError | None:
		if not block:
			return None
		meta = block["meta"]
		if meta["type"] == self.BT_NODE_DEFINE:
			if "name" in meta.keys():
				if self.has_node_type(meta["name"]):
					return GError(f"Invalid node definition, node name {meta["name"]} exists")
				if "from" in meta.keys() and not self.has_node_type(meta["from"]):
					return GError(
						f"Invalid node definition, node name {meta['from']} doesn't exists yet to create {meta['name']} node from it"
					)
				self.struct["node_" + meta["name"]] = block
				return None
			return GError("Invalid node definition, node name is required: 'node NodeName'")
		elif meta["type"] == self.BT_RELATION_DEFINE:
			if "name" in meta.keys():
				if not meta["from"]:
					return GError(f"Invalid relation definition, relation {meta["name"]} has no from")
				if not meta["to"]:
					return GError(f"Invalid relation definition, relation {meta["name"]} has no to")
				for f in meta["from"]:
					if not self.has_node_type(f):
						return GError(
							f"Invalid relation definition, node name {f} doesn't exists yet to create {meta['name']} relation from it"
						)
				for t in meta["to"]:
					if not self.has_node_type(t):
						return GError(
							f"Invalid relation definition, node name {t} doesn't exists yet to create {meta['name']} relation to it"
						)
				self.struct["relation_" + meta["name"]] = block
				return None
			return GError("Invalid relation definition, relation name is required: 'relation RelationName'")
		else:
			return GError(f"Invalid block: {meta["type"]}")

	def has_node_type(self, node: str) -> bool:
		"""
		Returns ``True`` if given ``node`` exists in parsed structure, ``False`` otherwise.
		"""
		return "node_" + node in self.struct

	def has_relation_type(self, relation: str) -> bool:
		"""
		Returns ``True`` if given ``relation`` exists in parsed structure, ``False`` otherwise.
		"""
		return "relation_" + relation in self.struct

	def is_relation_valid(self, relation: str, from_type: str, to_type: str) -> bool:
		"""
		Returns ``True`` if given ``relation`` is valid between ``from_type`` and ``to_type``, ``False`` otherwise.
		"""
		if not self.has_relation_type(relation):
			return False
		valid_from_list = self.struct["relation_" + relation]["meta"]["from"]
		valid_to_list = self.struct["relation_" + relation]["meta"]["to"]
		from_is_valid = from_type in valid_from_list
		check_from = from_type
		while not from_is_valid:
			if check_from in valid_from_list:
				from_is_valid = True
				break
			if "from" in self.struct["node_" + check_from]["meta"]:
				check_from = self.struct["node_" + check_from]["meta"]["from"]
			else:
				break
		if not from_is_valid:
			return False
		check_to = to_type
		if to_type in valid_to_list:
			return True
		while True:
			if check_to in valid_to_list:
				return True
			if "from" in self.struct["node_" + check_to]["meta"]:
				check_to = self.struct["node_" + check_to]["meta"]["from"]
			else:
				return False

def new_database() -> GraphiteDb:
	return GraphiteDb()

def _is_type_valid(ptype: str) -> bool:
	return ptype in ["int", "string", "date", "bool", "float"]

def _tokenize(line: str) -> list[str]:
	tokens = []
	current = ""
	current_index = 0
	while current_index < len(line):
		c = line[current_index]
		current_index += 1
		if current and c in ['"', "'"] and current[0] == c:
			tokens.append(current[1:])
			current = ""
			continue
		if current and current[0] in ['"', "'"] and current[-1] not in ['"', "'"]:
			current += c
			continue
		if c.isspace():
			if current:
				tokens.append(current)
				current = ""
			continue
		if c == "-" and current.isdigit():
			current += c
			continue
		if c == "-" and len(current.split("-")) == 2 and current.split("-")[0].isdigit() and current.split("-")[
			1].isdigit():
			current += c
			continue
		if c == "=":
			if current and current != "=":
				tokens.append(current)
				current = ""
			if current and current == "=":
				tokens.append(current + c)
				current = ""
				continue
		if c in [".", "(", ")", ":", ",", "-", "[", "]", ">"]:
			if current:
				tokens.append(current)
				current = ""
			tokens.append(c)
			continue
		current += c
	if current:
		tokens.append(current)
	return tokens

def _is_date_valid(date: str) -> bool:
	return date.count("-") == 2 and date.split("-")[0].isdigit() and date.split("-")[1].isdigit() and date.split("-")[
		2].isdigit()

def _load_properties(item: str, item_type: str, type_properties: dict, properties: list | dict) -> GError | dict:
	if len(type_properties) != len(properties):
		return GError(
			f"Invalid number of properties '{len(properties)}' for {item_type} type '{item_type}', required properties: {", ".join(type_properties)}"
		)
	if isinstance(properties, list):
		new_properties = {}
		for p in range(len(type_properties)):
			new_properties[list(type_properties.keys())[p]] = properties[p]
		properties = new_properties
	final_properties = {}
	for p in type_properties:
		if p not in properties:
			return GError(f"Invalid {item} properties, property '{p}' is required")
		if type_properties[p] == "int":
			if not isinstance(properties[p], int):
				return GError(f"Property '{p}' must be 'int' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "float":
			if not isinstance(properties[p], float):
				return GError(f"Property '{p}' must be 'float' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "string":
			if not isinstance(properties[p], str):
				return GError(f"Property '{p}' must be 'string' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "bool":
			if not isinstance(properties[p], bool):
				return GError(f"Property '{p}' must be 'bool' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "date":
			if not _is_date_valid(properties[p]):
				return GError(f"Property '{p}' must be 'date' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		else:
			return GError(f"Invalid property type '{type_properties[p]}' for {item} type '{item_type}'")
	return final_properties

def _parse_str(string: str) -> (int | str | bool | float, str):
	if string.isdigit():
		return int(string), "int"
	elif string.count(".") == 1 and string.split(".")[0].isdigit() and string.split(".")[1].isdigit():
		return float(string), "float"
	elif _is_date_valid(string):
		return string, "date"
	elif string == "true":
		return True, "bool"
	elif string == "false":
		return False, "bool"
	return string, "string"