from A.a import A


def test_a():
    my_a = A()
    assert my_a.name() == "A"
