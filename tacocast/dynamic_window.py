import itertools
import more_itertools

# Dynamic sliding window 
# Slide over an iterator, making chunks under target
# TODO: Explain better
# TODO: Move to a library?
class _dynamic_window:
    _current_sum = 0
    _current_class = 0
    _bump = False

    target: int = None
    max_target: int = None
    key = lambda _, x: x
    inclusive = False

    def __init__(self, target, hard_target=None, key=None, inclusive=None):
        self.target = target
        self.hard_target = hard_target
        self.key = key or self.key
        self.inclusive = inclusive or self.inclusive

    def __call__(self, pack):
        [v, next_v] = pack

        self._bump = False
        self._current_sum += self.key(v)

        if self._current_sum > self.target or (self.hard_target and next_v and self._current_sum + self.key(next_v) > self.hard_target):
            self._current_sum = self.key(v) if not self.inclusive else 0
            self._current_class += 1
            self._bump = True

        return self._current_class - 1 if self.inclusive and self._bump else self._current_class

def dynamic_window(iterator, target, *args, **kwargs):
    groups = itertools.groupby(more_itertools.windowed(itertools.chain(iterator, [None]), 2), key=_dynamic_window(target, *args, **kwargs))
    return ((pack[0] for pack in group[1]) for group in groups)