import copy

# Base class for all things seen in PLTRedex specification.
# TODO store line numbers for better error reporting?

class ASTBase:
    def __init__(self):
        self._attributes = {}

    def addattribute(self, key, val):
        if key in self._attributes:
            raise Exception('key {} is already assigned!'.format(key))
        self._attributes[key] = val
        return self

    def getattribute(self, key):
        return self._attributes[key]

    def removeattribute(self, key):
        del _self.attributes[key]
        return self

    def copyattributesfrom(self, node):
        assert isinstance(node, ASTBase)
        self._attributes = copy.copy(node._attributes)
        return self


