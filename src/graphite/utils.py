"""Utility functions, accessible directly from ``graphite``"""

class SecurityWarning(Warning):
	"""A marker warning class used for security-related concerns within Graphite.

	It may be raised or emitted when unsafe or potentially dangerous operations are detected.
	"""
