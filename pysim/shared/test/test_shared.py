from shared.shared import shared_function
import pytest

def test_shared():
    assert shared_function() == "shared"
