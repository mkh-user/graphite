"""
Tests for utility functions
"""
from src.graphite import engine
from src.graphite.graphite_engine import GraphiteEngine
from src.graphite.utils import SecurityWarning

class TestUtils:
	"""Test utility functions"""
	def test_engine_helper(self):
		"""Test engine helper function"""
		result = engine()

		assert isinstance(result, GraphiteEngine)

	def test_security_warning(self):
		"""Test SecurityWarning class"""
		warning = SecurityWarning("Test warning")

		assert isinstance(warning, Warning)
		assert "Test warning" in str(warning)
