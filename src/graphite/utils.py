"""
Utility functions, accessible directly from ``graphite``
"""

class SecurityWarning(Warning):
	"""A security warning."""

def node(node_type: str, **fields) -> str:
	"""Helper function to create node definitions"""
	lines = [f"node {node_type}"]
	for field_name, field_type in fields.items():
		lines.append(f"{field_name}: {field_type}")
	return "\n".join(lines)

def relation(name: str, from_type: str, to_type: str, **kwargs) -> str:
	"""Helper function to create relation definitions"""
	lines = [f"relation {name}"]
	if kwargs.get('both'):
		lines[0] += " both"
	if kwargs.get('reverse'):
		lines[0] += f" reverse {kwargs['reverse']}"

	direction = "->" if not kwargs.get('both') else "-"
	lines.append(f"{from_type} {direction} {to_type}")

	for field_name, field_type in kwargs.get('fields', {}).items():
		lines.append(f"{field_name}: {field_type}")

	return "\n".join(lines)

def engine():
	"""Create graphite engine instance"""
	from .engine import GraphiteEngine # pylint: disable=import-outside-toplevel
	return GraphiteEngine()
