.. _api:

API
*********************************************

The three modules a project imports. Everything public in
``cinnamon.configuration`` and ``cinnamon.registry`` is re-exported from
``cinnamon`` itself, so ``from cinnamon import Configuration`` and ``from
cinnamon.configuration import Configuration`` name the same class.
``cinnamon.cli`` holds the commands and is not re-exported.

=============================================
cinnamon.configuration
=============================================

.. automodule:: cinnamon.configuration
    :members:
    :undoc-members:
    :show-inheritance:

=============================================
cinnamon.registry
=============================================

.. automodule:: cinnamon.registry
    :members:
    :undoc-members:
    :show-inheritance:

=============================================
cinnamon.cli
=============================================

.. automodule:: cinnamon.cli
    :members:
    :undoc-members:
    :show-inheritance:

=============================================
cinnamon
=============================================

.. automodule:: cinnamon

The package re-exports the two modules above and documents nothing of its own.
