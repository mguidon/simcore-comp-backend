from shared.shared import shared_function

class A(object):
    def __init__(self):
        self._name = "A"

    def name(self):
        return self._name

    def shared(self):
        return shared_function()
