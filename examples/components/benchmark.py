import logging

from cinnamon.component import Component
from examples.components.data_loader import IMDBLoader
from examples.components.model import SVCModel
from examples.components.processor import LabelProcessor, TfIdfProcessor


class SVCBenchmark(Component):
    def __init__(
        self,
        data_loader: IMDBLoader,
        model: SVCModel,
        text_processor: TfIdfProcessor,
        label_processor: LabelProcessor,
    ):
        self.data_loader = data_loader
        self.model = model
        self.text_processor = text_processor
        self.label_processor = label_processor

    def run(self):
        logging.basicConfig(level=logging.INFO)

        train_df, val_df, test_df = self.data_loader.get_splits()

        x_train = self.text_processor.process(data=train_df, is_training_data=True)
        y_train = self.label_processor.process(data=train_df, is_training_data=True)

        x_val = self.text_processor.process(data=val_df)
        y_val = self.label_processor.process(data=val_df)

        x_test = self.text_processor.process(data=test_df)
        y_test = self.label_processor.process(data=test_df)

        train_info, val_info = self.model.fit(
            x_train=x_train, y_train=y_train, x_val=x_val, y_val=y_val
        )
        test_info = self.model.evaluate(x=x_test, y=y_test)

        logging.info(f"Train info:\n{train_info}")
        logging.info(f"Val info:\n{val_info}")
        logging.info(f"Test info:\n{test_info}")
