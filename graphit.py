from errors import *

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

	def q_add(self, node_type: str, node_id: str, properties: list | dict) -> dict[str, dict] | GError:
		"""
		Performs ``add`` query. This query creates a new node.

		**Note:** This method needs to be chained with ``update`` to change the database.

		:param node_type: Type of the node
		:param node_id: ID of the node
		:param properties: Properties of the node
		:return: ``GError`` or ``{node_id: node_object}``
		"""
		if not self.has_node_type(node_type):
			return GError(f"Invalid node type '{node_type}'")
		type_properties = self._list_properties(node_type)
		new_node = {
			"meta": {
				"type": node_type,
			},
			"properties": {},
		}
		p = _load_properties("node", node_type, type_properties, properties)
		if isinstance(p, GError):
			return p
		new_node["properties"] = p
		return {node_id: new_node}

	def q_rel(self, relation_type: str, from_node: str, to_node: str, properties: list | dict) -> dict[str, dict] | GError:
		"""
		Performs ``rel`` query. This query creates a new relation.

		**Note:** This query needs to be chained with ``update`` to change the database.

		:param relation_type: Type of the relation
		:param from_node: Source node
		:param to_node: Target node
		:param properties: Properties of the relation
		:return: ``GError`` or ``{relation_id: relation_object}``
		"""
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
			return GError(f"Relation type '{relation_type}' is not valid from '{from_node}' ({from_type}) to '{to_node}' ({to_type})")
		type_properties = self._list_relation_properties(relation_type)
		new_relation = {
			"meta": {
				"type": relation_type,
				"from": from_node,
				"to": to_node,
				"from_type": from_type,
				"to_type": to_type,
			},
			"properties": {},
		}
		if f"{relation_type} {from_node} {to_node}" in self.relations:
			print(f"Graphite Warning: Relation '{relation_type}' from '{from_node}' to '{to_node}' already exists, skipping.")
			return {f"{relation_type} {from_node} {to_node}": self.relations[f"{relation_type} {from_node} {to_node}"]}
		p = _load_properties("relation", relation_type, type_properties, properties)
		if isinstance(p, GError):
			return p
		new_relation["properties"] = p
		return {f"{relation_type} {from_node} {to_node}": new_relation}

	def q_disrel(self, target_relations: str | list[str]) -> dict[str, dict | GError]:
		"""
		Performs ``disrel`` query. This query removes given relation(s).

		**Note:** This query changes the database IMMEDIATELY.

		:param target_relations: One (ID string) or more (list of IDs) target relation IDs
		:return: Removed relation(s) ( {id: object} or {id: GError} pairs)
		"""
		result = {}
		if isinstance(target_relations, str):
			target_relations = [target_relations]
		for r in target_relations:
			if r in self.relations:
				result[r] = self.relations.pop(r)
			else:
				result[r] = GError("Non-existent relation")
		return result

	def q_rem(self, target_nodes: str | list[str]) -> dict[str, dict | GError]:
		"""
		Performs ``rem`` query. This query removes given node(s).

		**Note:** This query changes the database IMMEDIATELY.

		:param target_nodes: One (ID string) or more (list of IDs) target node IDs
		:return: Removed node(s) ( {id: object} or {id: GError} pairs).
		"""
		result = {}
		if isinstance(target_nodes, str):
			target_nodes = [target_nodes]
		for n in target_nodes:
			if n in self.nodes:
				result[n] = self.nodes.pop(n)
			else:
				result[n] = GError("Non-existent node")
		return result

	@staticmethod
	def q_set(target_id: str | list[str], field_name: str, value) -> dict[str, dict]:
		"""
		Performs ``set`` query. This query sets given value for given field in target items (node or relation).

		**Note:** This query needs to be chained with ``update`` to change the database.

		:param target_id: One (ID string) or more (list of IDs) target node IDs
		:param field_name: Name of the target field
		:param value: Value to set
		:return: Dictionary of {node_id: modified_object} pairs.
		"""
		result = {}
		if isinstance(target_id, str):
			target_id = [target_id]
		for i in target_id:
			result[i] = {field_name: value}
		return result

	def q_clr(self, target_id: str | list[str], field_name: str) -> dict[str, dict | GError]:
		"""
		Performs ``clr`` query. This query clears given field in target items (node or relation).

		**Note:** This query changes the database IMMEDIATELY.

		:param target_id: One (ID string) or more (list of IDs) target node IDs
		:param field_name: Name of the target field
		:return: Dictionary of {item_id: {field_name: value}} pairs.
		"""
		result = {}
		if isinstance(target_id, str):
			target_id = [target_id]
		for i in target_id:
			if i in self.nodes:
				if field_name in self.nodes[i]["properties"]:
					result[i] = {field_name: self.nodes[i]["properties"][field_name]}
					self.nodes[i]["properties"][field_name] = None
				else:
					result[i] = GError("Non-existent field")
			elif i in self.relations:
				if field_name in self.relations[i]["properties"]:
					result[i] = {field_name: self.relations[i]["properties"][field_name]}
					self.relations[i]["properties"][field_name] = None
				else:
					result[i] = GError("Non-existent field")
			else:
				result[i] = GError("Non-existent item")
		return result

	def q_sel(self, expression: str) -> dict[str, dict] | GError:
		"""
		Performs ``sel`` query. This query selects items (node or relation) from database.

		:param expression: A **Graphite Query** expression to select items
		:return: Dictionary of {item_id: object} pairs.
		"""
		tokens = _tokenize(expression)
		result = {}
		
		return result

	def q_filt(self, items: dict[str, dict] | list[str], expression: str) -> dict[str, dict | GError]:
		"""
		Performs ``filt`` query. This query filters given expression.

		:param items: One (ID string) or more (list of IDs) input item IDs
		:param expression: A **Graphite Query** expression, should return `true` to include item in result
		:return:
		"""
		pass

	def q_spath(self, from_node: str, to_node: str, relation_type: str = None, expression: str = None, exclude: str | list[str] = None) -> tuple[list[tuple[str, ]], ] | None:
		"""
		Performs ``spath`` query. This query returns the shortest path from given source node to given target node (if exists).

		:param from_node: Source node
		:param to_node: Target node
		:param relation_type: Type of relation, default value accepts all types
		:param expression: A **Graphite Query** expression to calculate value of each path, default value works with number of nodes in path
		:param exclude: One (ID string) or more (list of IDs) relation IDs to exclude from the result
		:return: ``None`` if no path exists, otherwise: ``([(first_relation, value), (second_relation, value), ...], final_value)``
		"""
		pass

	def q_sort(self, items: dict[str, dict] | list[str], expression: str) -> dict[str, dict] | list[str]:
		"""
		Performs ``sort`` query. This query sorts given items according to given expression.

		:param items: Dictionary of {item_id: object} pairs, or list of IDs
		:param expression: A **Graphite Query** expression to calculate value of each item
		:return: Sorted input (with same type).
		"""
		pass

	@staticmethod
	def q_limit(items: dict[str, dict] | list[str], count: int) -> dict[str, dict] | list[str]:
		"""
		Performs ``limit`` query. This query limits given items to specified number.

		:param items: Dictionary of {item_id: object} pairs, or list of IDs
		:param count: Count of items to limit.
		:return: Limited inputs with maximum size of ``count`` (with same type).
		"""
		if len(items) <= count:
			return items
		ids = list(items.keys())
		for i in range(count, len(ids)):
			items.pop(ids[i])
		return items

	def q_sum(self, items: dict[str, dict] | list[str], expression: str = None) -> int | float:
		"""
		Performs ``sum`` query. This query sums given items according to given expression.

		:param items: Dictionary of {item_id: object} pairs, or list of IDs
		:param expression: A **Graphite Query** expression to calculate value of each item
		:return: Integer or floating point number as sum.
		"""
		pass

	def q_avg(self, items: dict[str, dict] | list[str], expression: str = None) -> int | float:
		"""
		Performs ``avg`` query. This query averages given items according to given expression.

		:param items: Dictionary of {item_id: object} pairs, or list of IDs
		:param expression: A **Graphite Query** expression to calculate value of each item
		:return: Integer or floating point number as average.
		"""
		pass

	def q_min(self, items: dict[str, dict] | list[str], expression: str = None) -> dict[str, dict] | list[str]:
		"""
		Performs ``min`` query. This query returns minimum of given items according to given expression.

		:param items: Dictionary of {item_id: object} pairs, or list of IDs
		:param expression: A **Graphite Query** expression to calculate value of each item
		:return: Same type as ``items`` with just one item as minimum
		"""
		pass

	def q_max(self, items: dict[str, dict] | list[str], expression: str = None) -> dict[str, dict] | list[str]:
		"""
		Performs ``max`` query. This query returns maximum of given items according to given expression.

		:param items: Dictionary of {item_id: object} pairs, or list of IDs
		:param expression: A **Graphite Query** expression to calculate value of each item
		:return: Same type as ``items`` with just one item as maximum
		"""
		pass

	def q_obj(self, items: str | list[str]) -> dict[str, dict]:
		"""
		Performs ``obj`` query. This query returns {item_id: object} pair(s) for input.

		:param items: One (ID string) or more (list of IDs) input item IDs
		:return: Dictionary of {item_id: object} pairs for input
		"""
		pass

	def q_id(self, items: dict[str, dict]) -> list[str]:
		"""
		Performs ``id`` query. This query removes objects from input.

		:param items: Dictionary of {item_id: object} pairs
		:return: List of item_id values for input
		"""
		pass

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
								return GError(f"Parameter {tokens[index - 2]} is already defined for node {self.current_block["meta"]["name"]}")
							self.current_block["properties"][tokens[index - 2]] = t
							self.current_block["meta"]["properties_order"].append(tokens[index - 2])
						else:
							return GError(f"Invalid type '{t}' for parameter '{tokens[index - 2]}' in node {self.current_block["meta"]["name"]}")
					else:
						return GError(f"Invalid token in node definition block! Expected name, from, or property, got {t}")
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
								return GError(f"Parameter {tokens[index - 2]} is already defined for relation {self.current_block["meta"]["name"]}")
							self.current_block["properties"][tokens[index - 2]] = t
							self.current_block["meta"]["properties_order"].append(tokens[index - 2])
						else:
							return GError(f"Invalid type '{t}' for parameter '{tokens[index - 2]}' in relation {self.current_block["meta"]["name"]}")
					else:
						return GError(f"Invalid token in relation definition block! Expected name, both, reverse, from, to, or property, got {t}")
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
		result = self.q_add(node_type, node_id, properties)
		if isinstance(result, GError):
			return result
		self.nodes[node_id] = result[node_id]
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
			print(f"Graphite Warning: Relation '{relation_type}' from '{from_node}' to '{to_node}' already exists, skipping.")
			return None
		result = self.q_rel(relation_type, from_node, to_node, properties)
		if isinstance(result, GError):
			return result
		self.relations[list(result.keys())[0]] = list(result.values())[0]

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
					return GError(f"Invalid node definition, node name {meta['from']} doesn't exists yet to create {meta['name']} node from it")
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
						return GError(f"Invalid relation definition, node name {f} doesn't exists yet to create {meta['name']} relation from it")
				for t in meta["to"]:
					if not self.has_node_type(t):
						return GError(f"Invalid relation definition, node name {t} doesn't exists yet to create {meta['name']} relation to it")
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
		if current and current[0] in ['"', "'"] and current[-1] not in ['"', "'"]:
			current += c
			continue
		if current and c in ['"', "'"] and current[0] == c:
				tokens.append(current[1:])
				current = ""
				continue
		if c.isspace():
			if current:
				tokens.append(current)
				current = ""
			continue
		if c == "-" and current.isdigit():
			current += c
			continue
		if c == "-" and len(current.split("-")) == 2 and current.split("-")[0].isdigit() and current.split("-")[1].isdigit():
			current += c
			continue
		if c in [":", ",", "-", "[", "]", ">"]:
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
	return date.count("-") == 2 and date.split("-")[0].isdigit() and date.split("-")[1].isdigit() and date.split("-")[2].isdigit()

def _load_properties(item: str, item_type: str, type_properties: dict, properties: list | dict) -> GError | dict:
	if len(type_properties) != len(properties):
		return GError(f"Invalid number of properties '{len(properties)}' for {item_type} type '{item_type}', required properties: {", ".join(type_properties)}")
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
	else:
		return string, "string"
