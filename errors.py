class GError:
	def __init__(self, msg: str) -> None:
		self.message = msg

	def __str__(self) -> str:
		return self.message