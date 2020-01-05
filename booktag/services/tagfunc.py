import re
import statistics
import unicodedata


class TagCollector:
    def __init__(self):
        self._hit_map = {}

    def _normalize_value(self, value):
        normal = unicodedata.normalize('NFD', value).lower()
        return re.sub(r'[\W_]+', '', normal)

    def _register_hit(self, tag_hits, value):
        if value:
            key = self._normalize_value(str(value))
            tag_hits[key][1] = tag_hits.setdefault(key, [value, 0])[1] + 1

    def add(self, tagname, value):
        tag_hits = self._hit_map.setdefault(tagname, {})
        if isinstance(value, (list, tuple)):
            for item in value:
                self._register_hit(tag_hits, item)
        else:
            self._register_hit(tag_hits, value)

    def max(self, tagname):
        tag_hits = self._hit_map.get(tagname, {})
        if tag_hits:
            return max(tag_hits.values(), key=lambda v: v[1])[0]
        else:
            return None

    def median(self, tagname):
        tag_hits = self._hit_map.get(tagname, {})
        if tag_hits:
            median = statistics.median_low(x[1] for x in tag_hits.values())
            return [x[0] for x in tag_hits.values() if x[1] >= median]
        else:
            return None


# vim: ts=4 sw=4 sts=4 et ai
