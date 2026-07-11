import logging

from cinnamon.component import Component
from cinnamon.registry import RegistrationKey
from examples.components.data_loader import IMDBLoader
from examples.components.model import SVCModel
from examples.components.processor import LabelProcessor, TfIdfProcessor


class SVCBenchmark(Component):
    def __init__(
            self,
            data_loader: RegistrationKey,
            model: RegistrationKey,
            text_processor: RegistrationKey,
            label_processor: RegistrationKey,
    ):
        self.data_loader = data_loader
        self.model = model
        self.text_processor = text_processor
        self.label_processor = label_processor

    def run(self):
        logging.basicConfig(level=logging.INFO)

        data_loader = IMDBLoader.instantiate(self.data_loader)
        train_df, val_df, test_df = data_loader.get_splits()

        text_processor = TfIdfProcessor.instantiate(self.text_processor)
        label_processor = LabelProcessor.instantiate(self.label_processor)
        x_train = text_processor.process(data=train_df, is_training_data=True)
        y_train = label_processor.process(data=train_df, is_training_data=True)

        x_val = text_processor.process(data=val_df)
        y_val = label_processor.process(data=val_df)

        x_test = text_processor.process(data=test_df)
        y_test = label_processor.process(data=test_df)

        model = SVCModel.instantiate(self.model)
        train_info, val_info = model.fit(
            x_train=x_train, y_train=y_train, x_val=x_val, y_val=y_val
        )
        test_info = model.evaluate(x=x_test, y=y_test)

        logging.info(f"Train info:\n{train_info}")
        logging.info(f"Val info:\n{val_info}")
        logging.info(f"Test info:\n{test_info}")
