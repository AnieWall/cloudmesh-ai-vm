"""Simple in‑memory stub for the ``yamldb`` package.

The production code expects ``YamlDB`` to provide ``get`` and ``set`` methods
operating on a nested dictionary structure.  For unit tests we implement a
lightweight version that stores data in memory and supports dot‑notation keys.
"""


class YamlDB:
    """In‑memory representation of a YAML configuration file.

    The stub mimics the subset of the real ``YamlDB`` API used by the codebase:
    ``get`` and ``set`` with dot‑separated keys.  Persistence to disk is
    unnecessary for the tests, so the ``filename`` argument is ignored.
    """

    def __init__(self, filename=None):
        self.filename = filename
        self.store = {}

    def _navigate(self, key, create=False):
        """Navigate to the parent dictionary of *key*.

        Returns a tuple ``(parent_dict, final_key)``. ``create`` determines whether
        missing intermediate dictionaries are created.
        """
        parts = key.split('.')
        d = self.store
        for part in parts[:-1]:
            if create:
                d = d.setdefault(part, {})
            else:
                if not isinstance(d, dict) or part not in d:
                    return None, None
                d = d[part]
        return d, parts[-1]

    def get(self, key, default=None):
        parent, final = self._navigate(key, create=False)
        if parent is None:
            return default
        return parent.get(final, default)

    def set(self, key, value):
        parent, final = self._navigate(key, create=True)
        if parent is not None:
            parent[final] = value
