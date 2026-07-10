from typing import Any, Optional

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder

from cinnamon.component import Component


class TfIdfProcessor(Component):
    def __init__(self, **kwargs):
        self.vectorizer = TfidfVectorizer(**kwargs)

    def process(
        self,
        data: Optional[pd.DataFrame],
        is_training_data: bool = False,
    ) -> Optional[Any]:
        if data is None:
            return data

        if is_training_data:
            self.vectorizer.fit(data.x.values)

        return self.vectorizer.transform(data.x.values)


class LabelProcessor(Component):
    def __init__(self):
        self.label_encoder = LabelEncoder()

    def process(
        self, data: Optional[pd.DataFrame], is_training_data: bool = False
    ) -> Optional[Any]:
        if data is None:
            return data

        labels = data.y.values
        if is_training_data:
            self.label_encoder.fit(labels)

        return self.label_encoder.transform(labels)
