.. _component:

Component
*********************************************

A ``Component`` is any class that implements some logic (e.g., data loading, processing, etc...).

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

.. toctree::
   :maxdepth: 4
   :hidden:
   :caption: Contents:
   :titlesonly:

