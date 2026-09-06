.. _tutorial_conditions:

6. Conditions
*********************************************

A sweep generates combinations mechanically, and some of them make no sense — a
decoder wider than its encoder, a batch too large for the accumulation steps.
Conditions let a configuration reject itself.

.. code-block:: bash

    python examples/tutorial/06_conditions.py

.. literalinclude:: ../../../examples/tutorial/06_conditions.py
   :language: python
   :pyobject: AutoencoderConfig

Two two-valued axes give four combinations; one of them has a decoder wider than
its encoder, and the condition removes it.

===============================================
What to notice
===============================================

- Resolution returns **two sets rather than raising**. Invalid keys are not errors
  to fix; they are the combinations a sweep should skip, and each carries the reason
  it was excluded.
- That is the difference between a condition and a pydantic constraint. A
  constraint says *this value is impossible*; a condition says *this combination is
  not worth running*. The first should raise, the second should not.
- ``cmn-build`` writes both sets to ``registrations/``, so the excluded
  combinations and their reasons are on disk rather than in someone's memory.

===============================================
The whole file
===============================================

.. literalinclude:: ../../../examples/tutorial/06_conditions.py
   :language: python
   :linenos:

Next: :doc:`project_layout` — how all of this looks in a real project.
