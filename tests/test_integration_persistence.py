"""
Integration tests for persistence (save/load)
"""
import pytest
import os

from src.graphite import GraphiteEngine
from src.graphite.exceptions import FileSizeError, SafeLoadExtensionError, InvalidJSONError

# noinspection PyDeprecation
class TestPersistenceIntegration:
	"""Test persistence integration scenarios"""

	def test_save_and_load_json(self, populated_engine, temp_json_file):
		"""Test saving and loading JSON file"""
		engine = populated_engine

		# Save to file
		engine.save(temp_json_file)

		assert os.path.exists(temp_json_file)

		# Create new engine and load from file
		new_engine = GraphiteEngine()
		new_engine.load(temp_json_file, safe_mode=True)

		# Compare statistics
		original_stats = engine.stats()
		loaded_stats = new_engine.stats()

		assert original_stats == loaded_stats

		# Compare specific data
		original_alice = engine.get_node("person1")
		loaded_alice = new_engine.get_node("person1")

		assert original_alice.id == loaded_alice.id
		assert original_alice.type_name == loaded_alice.type_name
		assert original_alice.values == loaded_alice.values

		# Compare relations
		original_relations = engine.get_relations_from("person1")
		loaded_relations = new_engine.get_relations_from("person1")

		assert len(original_relations) == len(loaded_relations)

	def test_save_and_load_with_inheritance(self, engine_with_inheritance, temp_json_file):
		"""Test saving and loading with inheritance"""
		engine = engine_with_inheritance

		engine.save(temp_json_file)

		new_engine = GraphiteEngine()
		new_engine.load(temp_json_file, safe_mode=True)

		# Check inheritance was preserved
		admin_type = new_engine.node_types["Admin"]
		assert admin_type.parent is not None
		assert admin_type.parent.name == "User"

		user_type = new_engine.node_types["User"]
		assert user_type.parent is not None
		assert user_type.parent.name == "Entity"

		# Check data
		admin = new_engine.get_node("admin1")
		assert admin["id"] == "admin_entity"
		assert admin["username"] == "admin"
		assert admin["permissions"] == "all"

	def test_load_safe_security_checks(self, populated_engine, temp_json_file):
		"""Test safe loading security checks"""
		engine = populated_engine

		# Save valid file
		engine.save(temp_json_file)

		# Test with non-JSON extension
		non_json_file = temp_json_file.replace('.json', '.txt')
		os.rename(temp_json_file, non_json_file)

		new_engine = GraphiteEngine()

		with pytest.raises(SafeLoadExtensionError):
			new_engine.load_safe(non_json_file)

		# Cleanup
		os.unlink(non_json_file)

	def test_load_safe_file_size_check(self, populated_engine, temp_json_file):
		"""Test safe loading file size check"""
		engine = populated_engine

		# Save small file
		engine.save(temp_json_file)

		# Try to load with very small size limit
		new_engine = GraphiteEngine()

		with pytest.raises(FileSizeError):
			new_engine.load_safe(temp_json_file, max_size_mb=0.001)  # 1KB limit

	def test_load_unsafe_mode(self, populated_engine, temp_json_file):
		"""Test unsafe loading mode (for backward compatibility)"""
		import warnings

		engine = populated_engine
		engine.save(temp_json_file)

		new_engine = GraphiteEngine()

		# Should show deprecation warning but still work
		with warnings.catch_warnings(record=True) as w:
			warnings.simplefilter("always")
			new_engine.load(temp_json_file, safe_mode=False)

			# Check warning was issued
			assert len(w) > 0
			assert "Unsafe loading" in str(w[0].message)

		# Data should still be loaded
		assert len(new_engine.nodes) == len(engine.nodes)

	def test_load_invalid_json(self, temp_json_file):
		"""Test loading invalid JSON file"""
		# Create invalid JSON
		with open(temp_json_file, 'w') as f:
			f.write("Invalid JSON content {")

		engine = GraphiteEngine()

		with pytest.raises(InvalidJSONError):
			engine.load_safe(temp_json_file)

	def test_round_trip_complex_data(self, clean_engine, temp_json_file):
		"""Test round-trip with complex data structures"""
		engine = clean_engine

		# Create complex schema
		engine.define_node(
			"""
        node User
        name: string
        metadata: string
        scores: string
        """
		)

		engine.define_node(
			"""
        node Group
        name: string
        settings: string
        """
		)

		engine.define_relation(
			"""
        relation MEMBER_OF
        User -> Group
        role: string
        joined: date
        permissions: string
        """
		)

		# Create data with special characters
		engine.create_node("User", "user1", "Alice O'Connor", '{"key": "value"}', '[1, 2, 3]')
		engine.create_node("Group", "group1", "Admins © 2023", '{"theme": "dark"}')

		engine.create_relation(
			"user1", "group1", "MEMBER_OF",
			"Administrator", "2023-01-15", '{"access": "full"}'
		)

		# Save and load
		engine.save(temp_json_file)

		new_engine = GraphiteEngine()
		new_engine.load(temp_json_file, safe_mode=True)

		# Verify data integrity
		user = new_engine.get_node("user1")
		assert user["name"] == "Alice O'Connor"
		assert user["metadata"] == '{"key": "value"}'

		relation = new_engine.get_relations_from("user1", "MEMBER_OF")[0]
		assert relation["role"] == "Administrator"
		assert relation["permissions"] == '{"access": "full"}'

	def test_clear_and_reload(self, populated_engine, temp_json_file):
		"""Test clearing engine and reloading"""
		engine = populated_engine

		original_count = len(engine.nodes)

		# Save
		engine.save(temp_json_file)

		# Clear and verify empty
		engine.clear()
		assert len(engine.nodes) == 0
		assert len(engine.node_types) == 0

		# Reload
		engine.load(temp_json_file, safe_mode=True)

		assert len(engine.nodes) == original_count
		assert "Person" in engine.node_types
		assert "Company" in engine.node_types

	def test_multiple_save_load_cycles(self, clean_engine, temp_json_file):
		"""Test multiple save/load cycles"""
		engine = clean_engine

		# Cycle 1
		engine.define_node("node Test\nvalue: string")
		engine.create_node("Test", "t1", "Cycle1")
		engine.save(temp_json_file)

		# Cycle 2
		engine2 = GraphiteEngine()
		engine2.load(temp_json_file)
		engine2.create_node("Test", "t2", "Cycle2")
		engine2.save(temp_json_file)

		# Cycle 3
		engine3 = GraphiteEngine()
		engine3.load(temp_json_file)

		assert len(engine3.nodes) == 2
		assert engine3.get_node("t1")["value"] == "Cycle1"
		assert engine3.get_node("t2")["value"] == "Cycle2"
