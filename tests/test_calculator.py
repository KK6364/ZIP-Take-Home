"""Unit tests for the Calculator module."""
import pytest

from src.calculator import Calculator


@pytest.fixture
def calc():
    return Calculator()


class TestAdd:
    def test_positive_numbers(self, calc):
        assert calc.add(2, 3) == 5

    def test_negative_numbers(self, calc):
        assert calc.add(-1, -4) == -5

    def test_mixed_sign(self, calc):
        assert calc.add(-3, 7) == 4

    def test_floats(self, calc):
        assert calc.add(0.1, 0.2) == pytest.approx(0.3)

    def test_zero(self, calc):
        assert calc.add(0, 0) == 0


class TestSubtract:
    def test_basic(self, calc):
        assert calc.subtract(10, 4) == 6

    def test_negative_result(self, calc):
        assert calc.subtract(3, 9) == -6

    def test_same_values(self, calc):
        assert calc.subtract(5, 5) == 0


class TestMultiply:
    def test_basic(self, calc):
        assert calc.multiply(3, 4) == 12

    def test_by_zero(self, calc):
        assert calc.multiply(100, 0) == 0

    def test_negatives(self, calc):
        assert calc.multiply(-3, -4) == 12

    def test_mixed_sign(self, calc):
        assert calc.multiply(-3, 4) == -12


class TestDivide:
    def test_basic(self, calc):
        assert calc.divide(10, 2) == 5.0

    def test_float_result(self, calc):
        assert calc.divide(1, 3) == pytest.approx(0.3333, rel=1e-3)

    def test_divide_by_zero(self, calc):
        with pytest.raises(ZeroDivisionError, match="Cannot divide by zero"):
            calc.divide(5, 0)

    def test_negative_dividend(self, calc):
        assert calc.divide(-9, 3) == -3.0


class TestPower:
    def test_square(self, calc):
        assert calc.power(4, 2) == 16

    def test_zero_exponent(self, calc):
        assert calc.power(99, 0) == 1

    def test_negative_exponent(self, calc):
        assert calc.power(2, -1) == pytest.approx(0.5)


class TestHistory:
    def test_records_operations(self, calc):
        calc.add(1, 2)
        calc.subtract(5, 3)
        history = calc.history()
        assert len(history) == 2
        assert "1 + 2 = 3" in history[0]

    def test_history_is_copy(self, calc):
        calc.add(1, 1)
        h = calc.history()
        h.append("tampered")
        assert len(calc.history()) == 1

    def test_clear_history(self, calc):
        calc.add(1, 1)
        calc.clear_history()
        assert calc.history() == []
