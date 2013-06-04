from datazilla.util.debug import D

class Map(dict):
    def __init__(self, **map):
        dict.__init__(self, map)
        self.__dict__ = self

    def __str__(self):
        return dict.__str__(self)

    def __getattribute__(self, item):
        if item not in self: return None
        v=self[item]
        if isinstance(v, dict):
            return Map(**v)
        if not isinstance(v, list):
            return v
        D.error("Can not handle json lists, yet")

