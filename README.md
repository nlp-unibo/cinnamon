# Cinnamon

Cinnamon is a simple framework for general-purpose configuration and code logic de-coupling.
It was developed to offer two main functionalities:

**De-coupling**
   a code logic from its regulating parameters

**Re-use**
   of code logic without effort

## Features

#### General-purpose
   ``cinnamon`` is meant to **simplify** your code organization for better **re-use**.

#### Simple
``cinnamon`` is a small library that acts as a **high-level wrapper** for your projects.

#### Community-based
``cinnamon`` components and configurations can be imported from project!

#### Flexible
``cinnamon`` imposes **minimal APIs** for a quick learning curve and keeps freedom of coding.


## Documentation

Check the online documentation of [cinnamon](https://nlp-unibo.github.io/cinnamon/) for more information.

## Projects

The following projects have been developed with ``cinnamon``

- [``cinnamon-examples``](https://github.com/nlp-unibo/cinnamon_examples)

## Motivation

We describe a simple example to motivate cinnamon.

### Traditional approach

Consider a code logic that has to load some data.

```python

   class DataLoader:

      def load(...):
          data = read_from_file(folder_name=self.folder_name)
          return data
```

The data loader reads from a file located according to ``self.folder_name`` value.

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

### Cinnamon

Cinnamon keeps this <configuration, code logic> dichotomy where a configuration is written in **plain Python code**!

```python

from cinnamon.configuration import Configuration

class DataLoaderConfig(Configuration):

    @classmethod
    def default(cls):
        config = super().default()

        config.add(name='folder_name',
                   type_hint=str,
                   variants=['*folder_name1*', '*folder_name2*', ...],
                   description="Base folder name from which to look for data files.")
        return config
```

Cinnamon allows **high-level configuration definition** (constraints, type-checking, description, variants, etc...)

To quickly load any instance of our data loader, we

#### Register
Register the configuration via a **registration key** as <name, tags, namespace> tuple.

```python
      Registry.register_configuration(config_class=DataLoaderConfig,
                                      component_class=DataLoader,
                                      name='data_loader',
                                      tags={'example'},
                                      namespace='showcase')
```

#### Build
Build the ``DataLoader`` via the used **registration key**

   ```python

      data_loader = DataLoader.build_component(name='data_loader',
                                               tags={'example'},
                                               namespace='showcase')
      variant_loader = DataLoader.build_component(name='data_loader',
                                                  tags={'example', 'folder_name=*folder_name1*'},
                                                  namespace='showcase')
   ```


**That's it!** This is all of you need to use cinnamon.



**You are still free to code as you like!**

## Install


pip

      pip install cinnamon-core

git

      git clone https://github.com/nlp-unibo/cinnamon


## Contribute

Want to contribute with new ``Component`` and ``Configuration``?

Write your content and release it in a Github repository. That's all!

Cinnamon is meant to be a community project :)


## Contact

Don't hesitate to contact:
- Federico Ruggeri @ [federico.ruggeri6@unibo.it](mailto:federico.ruggeri6@unibo.it)

for questions/doubts/issues!