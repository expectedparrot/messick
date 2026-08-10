"""Stable public errors."""

class MessickError(Exception):
    def __init__(self, code: str, message: str, hint: str = "", **context):
        super().__init__(message)
        self.code, self.message, self.hint, self.context = code, message, hint, context

    def as_dict(self):
        value = {"code": self.code, "message": self.message, "context": self.context}
        if self.hint:
            value["hint"] = self.hint
        return value
