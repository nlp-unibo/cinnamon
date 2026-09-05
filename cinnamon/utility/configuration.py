import sys
from itertools import islice

__all__ = ["batched"]


# ``itertools.batched`` landed in Python 3.12. The two arms below are mutually
# exclusive on any single interpreter, so neither can be covered by a run that
# covers the other -- asking coverage to prove both is unsatisfiable. Behaviour
# is asserted directly in tests/test_utility_configuration.py instead.
if sys.version_info >= (3, 12):  # pragma: no cover
    from itertools import batched
else:  # pragma: no cover

    def batched(iterable, chunk_size):
        iterator = iter(iterable)
        return iter(lambda: tuple(islice(iterator, chunk_size)), tuple())
