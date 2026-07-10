from cinnamon.configuration import Configuration, Param
from cinnamon.registry import register_method


class SVCModelConfig(Configuration):
    C: float = Param(1.0, description="C parameter of SVC")
    kernel: str = Param("linear", description="The kernel of the SVC")
    class_weight: str = Param(
        "balanced",
        description="The weighting technique for addressing class imbalance."
        "Each sample in the training set receives a weight based on"
        " its class distribution",
    )

    @classmethod
    @register_method(
        name="model",
        tags={"svc"},
        namespace="examples",
        component="examples.components.SVCModel",
    )
    def default(cls):
        config = super().default()
        return config
