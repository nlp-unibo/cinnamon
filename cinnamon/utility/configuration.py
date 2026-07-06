import sys
from itertools import islice, product
from typing import Dict, List, Tuple

__all__ = ["batched"]


if sys.version_info >= (3, 12):
    from itertools import batched
else:

    def batched(iterable, chunk_size):
        iterator = iter(iterable)
        return iter(lambda: tuple(islice(iterator, chunk_size)), tuple())
