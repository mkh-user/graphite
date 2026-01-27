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

def _load_properties(item: str, item_type: str, type_properties: dict, properties: list | dict) -> ValueError | dict:
	if len(type_properties) != len(properties):
		return ValueError(f"Invalid number of properties '{len(properties)}' for {item_type} type '{item_type}', required properties: {", ".join(type_properties)}")
	if isinstance(properties, list):
		new_properties = {}
		for p in range(len(type_properties)):
			new_properties[list(type_properties.keys())[p]] = properties[p]
		properties = new_properties
	final_properties = {}
	for p in type_properties:
		if p not in properties:
			return ValueError(f"Invalid {item} properties, property '{p}' is required")
		if type_properties[p] == "int":
			if not isinstance(properties[p], int):
				return ValueError(f"Property '{p}' must be 'int' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "float":
			if not isinstance(properties[p], float):
				return ValueError(f"Property '{p}' must be 'float' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "string":
			if not isinstance(properties[p], str):
				return ValueError(f"Property '{p}' must be 'string' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "bool":
			if not isinstance(properties[p], bool):
				return ValueError(f"Property '{p}' must be 'bool' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		elif type_properties[p] == "date":
			if not _is_date_valid(properties[p]):
				return ValueError(f"Property '{p}' must be 'date' for {item} type '{item_type}'")
			final_properties[p] = properties[p]
		else:
			return ValueError(f"Invalid property type '{type_properties[p]}' for {item} type '{item_type}'")
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

	def parse_struct(self, code: str) -> ValueError | None:
		"""
		Parses a struct code into database, supports multiple runs in one database to expand current structure.

		**Note:** This function returns a ValueError if the structure is invalid, in this situation you need to create a new database object to ensure it is valid.

		:param code: ``str`` in ``.gdbs`` syntax
		:return: ``ValueError`` as error or ``None``
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
								return ValueError(f"Parameter {tokens[index - 2]} is already defined for node {self.current_block["meta"]["name"]}")
							self.current_block["properties"][tokens[index - 2]] = t
							self.current_block["meta"]["properties_order"].append(tokens[index - 2])
						else:
							return ValueError(f"Invalid type '{t}' for parameter '{tokens[index - 2]}' in node {self.current_block["meta"]["name"]}")
					else:
						return ValueError(f"Invalid token in node definition block! Expected name, from, or property, got {t}")
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
								return ValueError(f"Parameter {tokens[index - 2]} is already defined for relation {self.current_block["meta"]["name"]}")
							self.current_block["properties"][tokens[index - 2]] = t
							self.current_block["meta"]["properties_order"].append(tokens[index - 2])
						else:
							return ValueError(f"Invalid type '{t}' for parameter '{tokens[index - 2]}' in relation {self.current_block["meta"]["name"]}")
					else:
						return ValueError(f"Invalid token in relation definition block! Expected name, both, reverse, from, to, or property, got {t}")
				else:
					return ValueError(f"Invalid token: {t}")
				if t == self.RELATION_DEFINE:
					this_line_was_relation_define = True
				index += 1
			last_line_was_relation_define = this_line_was_relation_define
		if self.current_block:
			err = self._close_block(self.current_block)
			if err:
				return err
		return None

	def parse_data(self, data: str) -> ValueError | None:
		"""
		Parses a database code (usually ``.gdb`` file) to current database.

		:param data: ``str`` in ``.gdb`` syntax
		:return: ``ValueError`` as error or ``None``
		"""
		if not self.struct:
			return ValueError("Please parse structure before data")
		for line in data.splitlines():
			if not line.strip():
				continue
			tokens = _tokenize(line)
			if tokens[1] == ",":
				ntype = tokens.pop(0)
				if ntype == ",":
					return ValueError("Invalid syntax! Expected node type, got comma")
				if tokens.pop(0) != ",":
					return ValueError("Invalid syntax! Expected comma (',') after node type")
				nid = tokens.pop(0)
				if ntype == ",":
					return ValueError("Invalid syntax! Expected node id, got comma")
				if tokens.pop(0) != ",":
					return ValueError("Invalid syntax! Expected comma (',') after node id")
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
					return ValueError("Invalid syntax! Expected source node, got comma")
				if "".join(tokens[0:2]) != "-[":
					return ValueError("Invalid syntax! Expected '-[' after source node")
				tokens.pop(0)
				tokens.pop(0)
				rtype = tokens.pop(0)
				if rtype == ",":
					return ValueError("Invalid syntax! Expected relation type, got comma")
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
					return ValueError("Invalid syntax! Expected ']-' or ']>' after relation")
				if tokens.pop(0) not in ["-", ">"]:
					return ValueError("Invalid syntax! Expected '-' or '>' after relation")
				if not tokens:
					return ValueError("Invalid syntax! Missing target node")
				target = tokens.pop(0)
				if tokens:
					return ValueError(f"Invalid syntax! Expected end of line, got {tokens.pop(0)}")
				err = self.add_relation(rtype, source, target, properties)
				if err:
					return err
				continue
			else:
				return ValueError(f"Invalid syntax! Expected node ('..., ...') or relation ('... -[...') pattern")
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
	
	def add_node(self, node_type: str, node_id: str, properties: list | dict) -> ValueError | None:
		"""
		Adds a new node to database. Node must be valid in parsed structure. This is a mid-level API and not implemented for direct use, use ``parse_data`` instead.

		**Note:** When ``node_id`` parameter is duplicate, node will be overwritten.

		:param node_type: Type of the node, from defined types in structure.
		:param node_id: A unique identifier for the node. This is the fastest access way to node without query and relations to this node need this ID.
		:param properties: A dictionary or list of node properties.
		:return: ``ValueError`` as error or ``None``
		"""
		if not self.has_node_type(node_type):
			return ValueError(f"Invalid node type '{node_type}'")
		type_properties = self._list_properties(node_type)
		new_node = {
			"meta": {
				"type": node_type,
			},
			"properties": {},
		}
		p = _load_properties("node", node_type, type_properties, properties)
		if isinstance(p, ValueError):
			return p
		new_node["properties"] = p
		self.nodes[node_id] = new_node
		return None
	
	def add_relation(self, relation_type: str, from_node: str, to_node: str, properties: list | dict) -> ValueError | None:
		"""
		Adds a new relation to database. Relation must be valid in parsed structure. This is a mid-level API and not implemented for direct use, use ``parse_data`` instead.

		**Note:** When a relation from same type as ``relation_type`` exists between ``from_node`` and ``to_node``, skips call and prints a warning.

		:param relation_type: Type of the relation, from defined types in structure.
		:param from_node: Source node
		:param to_node: Target node
		:param properties: A dictionary or list of relation properties.
		:return: ``ValueError`` as error or ``None``
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
				return ValueError(f"Invalid relation type '{relation_type}'")
		if new_from and new_to:
			from_node = new_from
			to_node = new_to
		if from_node not in self.nodes:
			return ValueError(f"Node '{from_node}' does not exist")
		if to_node not in self.nodes:
			return ValueError(f"Node '{to_node}' does not exist")
		from_type = self.nodes[from_node]["meta"]["type"]
		to_type = self.nodes[to_node]["meta"]["type"]
		if not self.is_relation_valid(relation_type, from_type, to_type):
			return ValueError(f"Relation type '{relation_type}' is not valid from '{from_node}' ({from_type}) to '{to_node}' ({to_type})")
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
			return None
		p = _load_properties("relation", relation_type, type_properties, properties)
		if isinstance(p, ValueError):
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

	def _close_block(self, block: dict) -> ValueError | None:
		if not block:
			return None
		meta = block["meta"]
		if meta["type"] == self.BT_NODE_DEFINE:
			if "name" in meta.keys():
				if self.has_node_type(meta["name"]):
					return ValueError(f"Invalid node definition, node name {meta["name"]} exists")
				if "from" in meta.keys() and not self.has_node_type(meta["from"]):
					return ValueError(f"Invalid node definition, node name {meta['from']} doesn't exists yet to create {meta['name']} node from it")
				self.struct["node_" + meta["name"]] = block
				return None
			return ValueError("Invalid node definition, node name is required: 'node NodeName'")
		elif meta["type"] == self.BT_RELATION_DEFINE:
			if "name" in meta.keys():
				if not meta["from"]:
					return ValueError(f"Invalid relation definition, relation {meta["name"]} has no from")
				if not meta["to"]:
					return ValueError(f"Invalid relation definition, relation {meta["name"]} has no to")
				for f in meta["from"]:
					if not self.has_node_type(f):
						return ValueError(f"Invalid relation definition, node name {f} doesn't exists yet to create {meta['name']} relation from it")
				for t in meta["to"]:
					if not self.has_node_type(t):
						return ValueError(f"Invalid relation definition, node name {t} doesn't exists yet to create {meta['name']} relation to it")
				self.struct["relation_" + meta["name"]] = block
				return None
			return ValueError("Invalid relation definition, relation name is required: 'relation RelationName'")
		else:
			return ValueError(f"Invalid block: {meta["type"]}")

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