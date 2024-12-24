from itertools import product
from typing import Dict, List, Tuple

__all__ = [
    'get_dict_values_combinations'
]


def get_dict_values_combinations(
        params_dict: Dict
) -> Tuple[List[Dict], List[Dict]]:
    """
    Builds parameters combinations

    Args:
        params_dict: dictionary that has parameter names as keys and the list of possible values as values

    Returns:
        A list of dictionaries, each describing a parameters combination
    """

    params_combinations = []
    params_indexes = []

    keys = sorted(params_dict)
    comb_tuples = product(*(params_dict[key] for key in keys))
    index_tuples = product(*(list(range(len(params_dict[key]))) for key in keys))

    for comb_tuple, index_tuple in zip(comb_tuples, index_tuples):
        instance_params = {dict_key: comb_item for dict_key, comb_item in zip(keys, comb_tuple)}
        instance_indexes = {dict_key: index_item for dict_key, index_item in zip(keys, index_tuple)}
        if len(instance_params):
            params_combinations.append(instance_params)
            params_indexes.append(instance_indexes)

    return params_combinations, params_indexes
