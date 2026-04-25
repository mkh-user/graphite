"""
Unit tests for Migration utility
"""
import os
import pickle
import tempfile

import pytest

from src.graphite import GraphiteEngine, Migration

@pytest.mark.filterwarnings("ignore:'convert_pickle_to_json':PendingDeprecationWarning")
@pytest.mark.filterwarnings("ignore:Loading from pickle file")
# noinspection PyTypeChecker
class TestMigration:
	"""Test Migration utility class"""

	def test_convert_pickle_to_json_success(self, populated_engine, temp_json_file):
		"""Test successful pickle to JSON conversion"""
		engine = populated_engine

		# Create a pickle file first
		pickle_file = temp_json_file.replace('.json', '.db')

		# Save engine data in pickle format (simulating old format)
		data = {
			'node_types'       : engine.node_types,
			'relation_types'   : engine.relation_types,
			'nodes'            : engine.nodes,
			'relations'        : engine.relations,
			'node_by_type'     : dict(engine.node_by_type),
			'relations_by_type': dict(engine.relations_by_type),
			'relations_by_from': dict(engine.relations_by_from),
			'relations_by_to'  : dict(engine.relations_by_to)
		}

		with open(pickle_file, 'wb') as f:
			pickle.dump(data, f)

		# Convert to JSON
		json_file = temp_json_file

		Migration.convert_pickle_to_json(pickle_file, json_file, delete_original=False)

		assert os.path.exists(json_file)
		assert os.path.exists(pickle_file)  # Not deleted

		# Verify JSON file can be loaded
		converted_engine = GraphiteEngine()
		# noinspection PyDeprecation
		converted_engine.load(json_file, safe_mode=True)

		# Compare statistics
		original_stats = engine.stats()
		converted_stats = converted_engine.stats()

		assert original_stats == converted_stats

	def test_convert_pickle_to_json_delete_original(self, populated_engine, temp_json_file):
		"""Test conversion with delete_original=True"""
		engine = populated_engine

		pickle_file = temp_json_file.replace('.json', '.db')

		# Create pickle file
		data = {
			'node_types'       : engine.node_types,
			'relation_types'   : engine.relation_types,
			'nodes'            : engine.nodes,
			'relations'        : engine.relations,
			'node_by_type'     : dict(engine.node_by_type),
			'relations_by_type': dict(engine.relation_types),
			'relations_by_from': dict(engine.relations_by_from),
			'relations_by_to'  : dict(engine.relations_by_to)
		}

		with open(pickle_file, 'wb') as f:
			pickle.dump(data, f)

		json_file = temp_json_file

		Migration.convert_pickle_to_json(
			pickle_file, json_file, delete_original=True
		)

		assert os.path.exists(json_file)
		assert not os.path.exists(pickle_file)  # Should be deleted

	def test_convert_pickle_to_json_file_not_found(self, temp_json_file):
		"""Test conversion with non-existent pickle file"""
		pickle_file = "non_existent_file.db"
		json_file = temp_json_file

		with pytest.raises(FileNotFoundError):
			Migration.convert_pickle_to_json(pickle_file, json_file)

	def test_convert_pickle_to_json_invalid_pickle(self, temp_json_file):
		"""Test conversion with invalid pickle file"""
		pickle_file = temp_json_file.replace('.json', '.db')

		# Create an invalid pickle file
		with open(pickle_file, 'w', encoding="utf-8") as f:
			f.write("Not a pickle file")

		json_file = temp_json_file

		with pytest.raises(pickle.UnpicklingError):
			Migration.convert_pickle_to_json(pickle_file, json_file)

	@pytest.mark.filterwarnings("ignore::PendingDeprecationWarning")
	def test_detect_pickle_and_convert(self, populated_engine):
		"""Test detecting and converting pickle files in directory"""
		# Create temporary directory
		with tempfile.TemporaryDirectory() as temp_dir:
			# Create a pickle file
			pickle_file = os.path.join(temp_dir, "test.db")

			engine = populated_engine
			data = {
				'node_types'       : engine.node_types,
				'relation_types'   : engine.relation_types,
				'nodes'            : engine.nodes,
				'relations'        : engine.relations,
				'node_by_type'     : dict(engine.node_by_type),
				'relations_by_type': dict(engine.relations_by_type),
				'relations_by_from': dict(engine.relations_by_from),
				'relations_by_to'  : dict(engine.relations_by_to)
			}

			with open(pickle_file, 'wb') as f:
				pickle.dump(data, f)

			# Also create a JSON file (should be ignored)
			json_file = os.path.join(temp_dir, "test.json")
			with open(json_file, 'w', encoding="utf-8") as f:
				f.write('{"test": "data"}')

			# Create a non-pickle file (should be skipped)
			txt_file = os.path.join(temp_dir, "test.txt")
			with open(txt_file, 'w', encoding="utf-8") as f:
				f.write("text file")

			# Run detection and conversion
			Migration.detect_pickle_and_convert_to_json(temp_dir, pattern="*.db")

			# Check that JSON version was created
			expected_json = os.path.join(temp_dir, "test.json")
			# Note: original json file will be overwritten

			assert os.path.exists(expected_json)

			# Check pickle file still exists (delete_originals defaults to False)
			assert os.path.exists(pickle_file)
