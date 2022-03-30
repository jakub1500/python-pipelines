class Environment(dict):

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        return dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        return dict.__delitem__(self, key)

    def __contains__(self, key):
        return dict.__contains__(self, key)

env = Environment()