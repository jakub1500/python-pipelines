from threading import Lock

class Environment(dict):

    def __init__(self, *args, **kwargs):
        self.update(*args, **kwargs)
        self.mutex = Lock()

    def __getitem__(self, key):
        return self._call_func_with_lock(dict.__getitem__, self, key)

    def __setitem__(self, key, value):
        return self._call_func_with_lock(dict.__setitem__, self, key, value)

    def __delitem__(self, key):
        return self._call_func_with_lock(dict.__delitem__, self, key)

    def __contains__(self, key):
        return self._call_func_with_lock(dict.__contains__, self, key)

    def _call_func_with_lock(self, function, *args):
        self.mutex.acquire()
        ret_val = function(*args)
        self.mutex.release()
        return ret_val

env = Environment()