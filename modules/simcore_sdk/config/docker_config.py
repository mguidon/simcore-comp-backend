""" Basic configuration file for docker registry

"""

class Config():
    def __init__(self):
        self._registry = "masu.speag.com"
        self._user = "z43"
        self._pwd = "z43"
    
    def registry(self):
        return self._registry + "/v2"
    
    def user(self):
        return self._user

    def pwd(self):
        return self._pwd