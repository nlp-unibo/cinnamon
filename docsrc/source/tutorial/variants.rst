.. _tutorial_variants:

3. Variants
*********************************************

This is what cinnamon is for. A researcher rarely wants *a* configuration; they
want the twelve configurations that differ along two axes, each one addressable and
reproducible.

.. code-block:: bash

    python examples/tutorial/03_variants.py

Declare the axes and resolution enumerates the combinations, giving each a key
derived from its values.

.. literalinclude:: ../../../examples/tutorial/03_variants.py
   :language: python
   :pyobject: ClassifierConfig

Three learning rates times two hidden sizes is six configurations, out of six
lines. ``dropout`` has no variants, so it stays fixed everywhere and never appears
in a tag.

===============================================
What to notice
===============================================

- ``variants`` lists the *alternatives* to the default. The default is part of the
  sweep too, which is why two values in ``variants`` give three configurations.
- The tags are derived from the values, so a key is stable across runs and across
  machines. Rerun the file and ``learning_rate=0.01--hidden_size=256`` still names
  the same experiment. That is what makes a result addressable six months later.
- Nobody wrote those keys down. They are a consequence of the declaration, which is
  also why they cannot fall out of step with it.

===============================================
The whole file
===============================================

.. literalinclude:: ../../../examples/tutorial/03_variants.py
   :language: python
   :linenos:

Next: :doc:`dependencies` — configurations that reference other registrations.
