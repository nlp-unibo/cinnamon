from itertools import product
from typing import Dict, List

__all__ = [
    'get_dict_values_combinations'
]


def get_dict_values_combinations(
        params_dict: Dict
) -> List[Dict]:
    """
    Builds parameters combinations

    Args:
        params_dict: dictionary that has parameter names as keys and the list of possible values as values
        (see model_gridsearch.json for more information)

    Returns:
        A list of dictionaries, each describing a parameters combination
    """

    params_combinations = []

    keys = sorted(params_dict)
    comb_tuples = product(*(params_dict[key] for key in keys))

    for comb_tuple in comb_tuples:
        instance_params = {dict_key: comb_item for dict_key, comb_item in zip(keys, comb_tuple)}
        if len(instance_params):
            params_combinations.append(instance_params)

    return params_combinations
