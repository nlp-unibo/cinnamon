# Cinnamon

Cinnamon is a simple framework for general-purpose configuration and code logic de-coupling.
It was developed to offer two main functionalities:

**De-coupling**
   a code logic from its regulating parameters

**Re-use**
   of code logic without effort

## Features

**General-purpose**
   ``cinnamon`` is meant to **simplify** your code organization for better **re-use**.

**Simple**
   ``cinnamon`` is a small library that acts as a **high-level wrapper** for your projects.

**Modular**
   ``cinnamon`` is shipped in **several small packages** to meet different requirements.

**Community-based**
   the ``Component`` and ``Configuration`` you define can be **imported from/exported to** other users and project!

**Flexible**
   ``cinnamon`` imposes **minimal APIs** for a quick learning curve.

**You are still free to code as you like!**

## Documentation

Check the online documentation of [cinnamon-core](https://nlp-unibo.github.io/cinnamon_core/) for more information.

Check also the central [cinnamon](https://nlp-unibo.github.io/cinnamon/) documentation to overview all cinnamon packages!

## Background

Consider a code logic that has to load some data.

```python

   class DataLoader:

      def load(...):
          data = read_from_file(folder_name=self.folder_name)
          return data
```

The data loader reads from a file located according to ``self.folder_name``'s value.

If ``self.folder_name`` has multiple values, we can use the same code logic to load data from different folders.

Hypothetically, we would define multiple data loaders:

```python

   data_loader_1 = DataLoader(folder_name='*folder_name1*')
   data_loader_2 = DataLoader(folder_name='*folder_name2*')
   ...
```

Now, if the data loader code block is used in a project, we require some code modularity to avoid
defining several versions of the same script.
One common solution is to rely on **configuration files** (e.g., JSON file).

```python
   {
      'data_loader' : {
         'folder_name': '*folder_name1*'
      }
   }
```

The main script is modified to load our configuration file so that each code logic is properly initialized.


## Cinnamon

Well, cinnamon keeps this <configuration, code logic> dichotomy where a configuration is written in **plain Python code**!

```python

class DataLoaderConfig(Configuration):

    @classmethod
    def get_default(cls):
        config = super().default()

        config.add(name='folder_name',
                   type_hint=str,
                   is_required=True,
                   variants=['*folder_name1*', '*folder_name2*', ...],
                   description="Base folder name from which to look for data files.")
        return config
```

Cinnamon allows **high-level configuration definition** (constraints, type-checking, description, variants, etc...)

To quickly load any instance of our data loader code logic, we

**register**
   the configuration via a **registration key**

```python

      key = RegistrationKey(name='data_loader', namespace='showcase')
      Registry.add_configuration_variants_from_key(config_class=DataLoaderConfig,
                                 key=key)
```

**bind**
   the configuration to its code logic: ``DataLoaderConfig`` --> ``DataLoader``

   ```python


      Registry.bind(config_class=DataLoaderConfig,
                    component_class=DataLoader,
                    key=key)
   ```

**build**
   the ``DataLoader`` code logic with a specific configuration instance via the used **registration key**

   ```python

      variant_key = RegistrationKey(name='data_loader', tags={'folder_name=*folder_name1*'}, namespace='showcase')
      data_loader = Registry.build_component(key=variant_key)
   ```


**That's it!** This is all of you need to use cinnamon.


## Features

**General-purpose**
   ``cinnamon`` is meant to **simplify** your code organization for better **re-use**.

**Simple**
   ``cinnamon`` is a small library that acts as a **high-level wrapper** for your projects.

**Modular**
   ``cinnamon`` is shipped in **several small packages** to meet different requirements.

**Community-based**
   the ``Component`` and ``Configuration`` you define can be **imported from/exported to** other users and project!

**Flexible**
   ``cinnamon`` imposes **minimal APIs** for a quick learning curve.



**You are still free to code as you like!**

## Install


pip

      pip install cinnamon-core

git

      git clone https://github.com/federicoruggeri/cinnamon_core


## Contribute

Want to contribute with new ``Component`` and ``Configuration``?

Feel free to submit a merge request!

Cinnamon is meant to be a community project :)


## Contact

Don't hesitate to contact:
- Federico Ruggeri @ [federico.ruggeri6@unibo.it](mailto:federico.ruggeri6@unibo.it)

for questions/doubts/issues!