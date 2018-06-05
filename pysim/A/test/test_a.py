from A.a import A
import pytest


def test_a():
    my_a = A()
    assert my_a.name() == "A"
    assert my_a.shared() == "shared"
