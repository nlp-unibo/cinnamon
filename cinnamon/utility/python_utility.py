import inspect
from itertools import product
from typing import Dict, List


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


# TODO: remove?
# Taken from: https://stackoverflow.com/questions/2521901/get-a-list-tuple-dict-of-the-arguments-passed-to-a-function
def get_function_arguments():
    """
    Gets the arguments of a function.

    Returns:
        A dictionary with argument names as keys and argument values as values.
    """

    frame = inspect.currentframe().f_back
    keys, _, _, values = inspect.getargvalues(frame)
    kwargs = {}
    for key in keys:
        if key != 'self':
            kwargs[key] = values[key]
    return kwargs


# TODO: remove?
def get_function_signature(
        function
):
    """
    Returns the static signature of a method.

    Args:
        function: the method from which to get its signature

    Returns:
        The argument names that define the input method signature
    """

    arguments = inspect.signature(function)
    return arguments.parameters.keys()


__all__ = ['get_dict_values_combinations', 'get_function_arguments', 'get_function_signature']
