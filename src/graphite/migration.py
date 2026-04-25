"""
Helper module to update Graphite databases and handle other migrations
"""
import glob
import os
import pickle
import warnings

from .engine import GraphiteEngine
from .utils import SecurityWarning

class Migration:
	"""Utility for migrating from older versions"""

	@staticmethod
	def convert_pickle_to_json(
		pickle_file: str, json_file: str, delete_original: bool = False
	) -> None:
		"""
		Convert a pickle file to JSON format

		:param pickle_file: Path to existing pickle file
		:param json_file: Path for new JSON file
		:param delete_original: Whether to delete pickle file after conversion

		:return: None
		"""
		warnings.warn(
			"'convert_pickle_to_json' will be deprecated because of security reasons. "
			"Please convert your pickle files to JSON and don't use old files anymore.",
			PendingDeprecationWarning
		)

		# Load from pickle (with safety warnings)
		warnings.warn(
			f"Loading from pickle file: {pickle_file}. "
			"Pickle files can contain malicious code. "
			"Only load files from trusted sources.",
			SecurityWarning
		)

		with open(pickle_file, 'rb') as f:
			data = pickle.load(f)

		# Create a new engine with the loaded data
		converter_engine = GraphiteEngine()

		# Restore data structures
		converter_engine.node_types = data['node_types']
		converter_engine.relation_types = data['relation_types']
		converter_engine.nodes = data['nodes']
		converter_engine.relations = data['relations']
		converter_engine.node_by_type = data['node_by_type']
		converter_engine.relations_by_type = data['relations_by_type']
		converter_engine.relations_by_from = data['relations_by_from']
		converter_engine.relations_by_to = data['relations_by_to']

		# Save to JSON
		converter_engine.save(json_file)

		if delete_original:
			os.unlink(pickle_file)
			print(f"Converted {pickle_file} to {json_file} and deleted original")
		else:
			print(f"Converted {pickle_file} to {json_file}")

	@staticmethod
	def detect_pickle_and_convert_to_json(
		directory: str, pattern: str = "*.db", delete_originals: bool = False
	) -> None:
		"""
		Find and convert all pickle files in a directory

		:param directory: Directory to scan
		:param pattern: File pattern to match (default: *.db)
		:param delete_originals: Whether to delete pickle files after conversion

		:return: None
		"""
		for pickle_file in glob.glob(os.path.join(directory, pattern)):
			if pickle_file.endswith('.json'):
				continue

			json_file = pickle_file.rsplit('.', 1)[0] + '.json'

			try:
				# Quick check if it's a pickle file
				with open(pickle_file, 'rb') as f:
					# Try to read pickle header
					header = f.read(4)
					if header == b'\x80\x04' or header.startswith(b'\x80'):  # Pickle protocol 4
						Migration.convert_pickle_to_json(
							pickle_file, json_file, delete_originals
						)
			except Exception as e: # pylint: disable=broad-exception-caught
				# Not a pickle file or can't read
				print(f"File '{pickle_file}' skipped: {e}")
