import json

def jstr(obj):
    """Shortcut to printing out an obj as formatted json."""
    return json.dumps(obj, indent=4)

def nvl(a, b):
    #pick the first none-null value
    if a is None:
        return b
    return a


def error(description, cause):
    #how to raise and exception with a trace for the cause too?
    raise Exception(description, cause)
