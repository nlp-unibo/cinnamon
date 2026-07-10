from typing import Any, Dict, Optional, Tuple

from sklearn.metrics import accuracy_score, f1_score
from sklearn.svm import SVC

from cinnamon.component import Component


class SVCModel(Component):
    def __init__(self, C: float, kernel: str, class_weight: Optional[str] = "balanced"):
        self.C = C
        self.kernel = kernel
        self.class_weight = class_weight

        self.model = SVC(C=self.C, kernel=self.kernel, class_weight=self.class_weight)

    def fit(
        self,
        x_train: Any,
        y_train: Any,
        x_val: Optional[Any] = None,
        y_val: Optional[Any] = None,
    ) -> Tuple[Dict[str, float], Optional[Dict[str, float]]]:
        self.model.fit(X=x_train, y=y_train)
        train_info = self.evaluate(x=x_train, y=y_train)

        if x_val is not None:
            val_info = self.evaluate(x=x_val, y=y_val)
            return train_info, val_info

        return train_info, None

    def evaluate(self, x: Any, y: Any) -> Dict[str, float]:
        predictions = self.predict(x=x)
        f1 = f1_score(y_pred=predictions, y_true=y)
        acc = accuracy_score(y_pred=predictions, y_true=y)

        return {"f1": f1, "acc": acc}

    def predict(self, x: Any) -> Any:
        return self.model.predict(X=x)
