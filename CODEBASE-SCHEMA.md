# Codebase schema

This schema covers the registration path only.

## cinnamon/registry.py

The module depends on `cinnamon.configuration`, `cinnamon.utility.registration`, `cinnamon.utility.dependencies`, and `cinnamon.utility.exceptions`.
`Namespace.key` builds a `RegistrationKey` in its own namespace.
`register_method`, `register_class`, and `Registry.register_configuration` call `_registration_key`, which takes either a key or a name, tags, and namespace.
Both decorators then call `_buffer` with a `BufferedRegistration` or a `BufferedClassRegistration`, each holding that key.
`Registry.build` calls `parse_configuration_files`, which runs `NamespaceExtractor.process` on every configuration script.
`Registry.load_registrations` executes those scripts, and each buffered registration reaches `Registry.register_configuration_from_key`.
For an external directory, `Registry.load_registrations` calls `qualified_package` and, when the package cannot be imported, `locate_module`.
`Registry.load_registrations` adds `sys.path` entries only through `Registry.add_to_sys_path`, which records them in `_SYS_PATH_ENTRIES`.
`Registry.snapshot`, `Registry.restore`, and `Registry.forget_loaded_modules` read `_SYS_PATH_ENTRIES` to put entries back or take them off.
`Registry.register_configuration_from_key` loads a dependency's external directory with `Registry.load_registrations(external=True)`.
`Registry.register_configuration` passes the key it builds or copies to `Registry.register_configuration_from_key`, which stores a key as given.
`Registry.expand_configuration` records the value of every variant parameter of a key in `_VARIANT_VALUES`, defaults included, and the tags it generated in `_GENERATED_TAGS`.
`Registry.retrieve_keys` calls `match_tags`, `_match_variants`, and, for `untagged`, `Registry.retrieve_user_tags`, which reads `_GENERATED_TAGS`.
`Registry.retrieve_variant_values` reads `_VARIANT_VALUES` for one key.
`Registry.freeze_runtime` and `Registry.install_runtime` carry `_VARIANT_VALUES` and `_GENERATED_TAGS` with each key.
`select_tags` in `cinnamon/utility/inquirer.py` calls `Registry.retrieve_keys(untagged=True)` for its untagged choice.

## cinnamon/utility/registration.py

`NamespaceExtractor.process` calls `_bindings` and then visits the module.
`visit_FunctionDef`, `visit_ClassDef`, and `visit_Call` call `_registered_namespace` on each registration they recognise.
`_registered_namespace` reads `namespace=` through `_namespace`, or a key argument through `_key_namespace`.
`_namespace` and `_key_namespace` call `_lookup`, which follows imports through `_import_source` and `_bindings`.
