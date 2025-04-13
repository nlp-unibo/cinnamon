.. _component:

Component
*********************************************

A ``Component`` is any class that implements some logic (e.g., data loading, processing, etc...).

.. image:: img/component.png
    :scale: 70%
    :align: center

Cinnamon does not impose any APIs to your existing code, except that any class has to inherit from ``Component``.

The below code example

.. code-block:: python

    class CustomClass:

        def __init__(self, x):
            self.x = x

can be quickly integrated into cinnamon by inheriting from ``Component``.

.. code-block:: python

    class CustomClass(cinnamon.component.Component):

        def __init__(self, x):
            self.x = x

The same applies for more articulated python classes.