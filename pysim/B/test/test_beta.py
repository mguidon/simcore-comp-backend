from B.b import B
import pytest

def test_b():
    my_b = B()
    assert my_b.name() == "B"
