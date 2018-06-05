from A.a import A

class B(object):
    def __init__(self):
        self._name = "B"
        self.a = A()
    def name(self):
        return self._name
