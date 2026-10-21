# Codebase schema

This schema covers the registration path only.

## cinnamon/registry.py

The module depends on `cinnamon.configuration`, `cinnamon.utility.registration`, `cinnamon.utility.dependencies`, and `cinnamon.utility.exceptions`.
`Namespace.key` builds a `RegistrationKey` in its own namespace.
`register_method`, `register_class`, and `Registry.register_configuration` call `_registration_key`, which takes either a key or a name, tags, and namespace.
Both decorators then call `_buffer` with a `BufferedRegistration` or a `BufferedClassRegistration`, each holding that key.
`Registry.build` calls `parse_configuration_files`, which runs `NamespaceExtractor.process` on every configuration script.
`Registry.load_registrations` executes those scripts, and each buffered registration reaches `Registry.register_configuration_from_key`.
`Registry.register_configuration` passes the key it builds or copies to `Registry.register_configuration_from_key`, which stores a key as given.

## cinnamon/utility/registration.py

`NamespaceExtractor.process` calls `_bindings` and then visits the module.
`visit_FunctionDef`, `visit_ClassDef`, and `visit_Call` call `_registered_namespace` on each registration they recognise.
`_registered_namespace` reads `namespace=` through `_namespace`, or a key argument through `_key_namespace`.
`_namespace` and `_key_namespace` call `_lookup`, which follows imports through `_import_source` and `_bindings`.
