"""Simple calculator module."""


class Calculator:
    """A basic calculator supporting arithmetic and history tracking."""

    def __init__(self):
        self._history = []

    def add(self, a, b):
        """Return a + b."""
        result = a + b
        self._history.append(f"{a} + {b} = {result}")
        return result

    def subtract(self, a, b):
        """Return a - b."""
        result = a - b
        self._history.append(f"{a} - {b} = {result}")
        return result

    def multiply(self, a, b):
        """Return a * b."""
        result = a * b
        self._history.append(f"{a} * {b} = {result}")
        return result

    def divide(self, a, b):
        """Return a / b. Raises ZeroDivisionError if b is 0."""
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        result = a / b
        self._history.append(f"{a} / {b} = {result}")
        return result

    def power(self, base, exp):
        """Return base raised to exp."""
        result = base ** exp
        self._history.append(f"{base} ** {exp} = {result}")
        return result

    def history(self):
        """Return a copy of the operation history."""
        return list(self._history)

    def clear_history(self):
        """Clear operation history."""
        self._history.clear()
