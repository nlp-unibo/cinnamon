from cinnamon.configuration import Configuration, Param
from cinnamon.registry import RegistrationKey, register_method


class SVCBenchmarkConfig(Configuration):
    data_loader: RegistrationKey = Param(
        RegistrationKey(name="data_loader", tags={"imdb"}, namespace="examples"),
        description="Data loader",
    )
    text_processor: RegistrationKey = Param(
        RegistrationKey(name="processor", tags={"tf-idf"}, namespace="examples"),
        description="Text processor",
    )
    label_processor: RegistrationKey = Param(
        RegistrationKey(name="processor", tags={"label"}, namespace="examples"),
        description="Label processor",
    )
    model: RegistrationKey = Param(
        RegistrationKey(name="model", tags={"svc"}, namespace="examples"),
        description="Model",
    )

    @classmethod
    @register_method(
        name="benchmark",
        tags={"svc"},
        namespace="examples",
        component="examples.components.benchmark.SVCBenchmark",
        run_method="run",
        resolve_automatically=False
    )
    def default(cls):
        config = super().default()
        return config
