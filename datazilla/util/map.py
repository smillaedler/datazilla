from datazilla.util.debug import D

class Map(dict):
    def __init__(self, **map):
        dict.__init__(self, map)
        self.__dict__ = self

    def __str__(self):
        return dict.__str__(self)

    def __getitem__(self, item):
        return Map.__getattribute__(self, item)

    def __getattribute__(self, item):
        if item.find(".")>=0:
            s=self
            for n in item.split("."):
                s= Map.__getattribute__(s, n)
            return s

        if item not in self: return None
        v=dict.__getitem__(self, item)
        if v is None:
            return Map()
        if isinstance(v, dict):
            return Map(**v)
        if not isinstance(v, list):
            return v
        D.error("Can not handle json lists, yet")

