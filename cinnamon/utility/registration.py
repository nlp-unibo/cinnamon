from __future__ import annotations

import ast
import importlib
import types
from enum import Enum
from importlib.machinery import PathFinder
from pathlib import Path
from typing import AbstractSet, Any, List, Optional, Tuple, Union

__all__ = [
    "NamespaceExtractor",
    "Tags",
    "TAGGABLE_TYPES",
    "match_name",
    "match_namespace",
    "match_tags",
    "import_class_from_string",
    "locate_module",
]


# An AbstractSet so that both set and frozenset satisfy it: RegistrationKey
# normalises its tags to a frozenset, which is not a Set[str].
Tags = Optional[AbstractSet[str]]

TAGGABLE_TYPES = [str, int, float, bool, types.NoneType, Enum]


class NamespaceExtractor(ast.NodeVisitor):
    """
    Finds the namespaces a configuration module registers into, without running it.

    ``Registry.build`` needs to know which namespaces live in which directory
    before it imports anything, so this reads the decorators and registration
    calls straight from the AST.

    All three ways of registering are read: ``@register_method`` on a method,
    ``@register_class`` on a configuration class, and a ``register_configuration``
    call inside a ``@register`` function.

    A namespace is discovered when it is a literal, a module-level constant
    bound to one -- ``NAMESPACE = "myproject"`` at the top of the file is the
    common idiom -- or such a constant imported from another module, which is
    how a project keeps one namespace for many configuration files. A
    ``Namespace("myproject")`` constant reads as its literal. A ``key=``
    argument is followed to its binding, ``FR = NAMESPACE.key(...)`` or
    ``FR = RegistrationKey(..., namespace=...)``, and the namespace is read
    from there. Imports are followed on the filesystem, by parsing the module
    they name; nothing is executed, and nothing needs to be importable yet.

    Anything computed at runtime cannot be read without executing the module,
    and is skipped rather than guessed at: the previous implementation took the
    text after ``namespace=`` and would record the string ``"NAMESPACE"`` as
    though it were a real namespace.
    """

    REGISTER_DECORATOR = "register"
    REGISTER_METHOD_DECORATOR = "register_method"
    REGISTER_CLASS_DECORATOR = "register_class"
    REGISTRATION_CALLS = frozenset({"register_configuration"})
    NAMESPACE_CLASS = "Namespace"
    KEY_METHOD = "key"
    KEY_CLASS = "RegistrationKey"

    def __init__(self):
        self.namespaces: List[str] = []
        self.register_flag = False
        self._constants: dict = {}
        self._calls: dict = {}
        self._imports: dict = {}
        self._filename: Path = Path()

    def process(self, filename: Path) -> List[str]:
        # Reset: one extractor instance is reused for every file in a build, and
        # a flag left set by one module used to leak into the next.
        self.register_flag = False
        self.namespaces = []
        self._filename = filename

        with filename.open("r") as f:
            tree = ast.parse(f.read(), filename)

        self._constants, self._calls, self._imports = self._bindings(tree)
        self.visit(tree)

        namespaces = list(self.namespaces)
        self.namespaces.clear()
        return namespaces

    @classmethod
    def _bindings(cls, tree: ast.Module) -> Tuple[dict, dict, dict]:
        """Module-level string constants, call bindings and ``from`` imports.

        ``NAME = "literal"`` and ``NAME = Namespace("literal")`` bind a
        string. Any other ``NAME = call(...)`` is kept as its call node, which
        is how a key declared with ``NAMESPACE.key(...)`` is found again.
        """
        constants: dict = {}
        calls: dict = {}
        imports: dict = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports[alias.asname or alias.name] = (
                        node.module,
                        node.level,
                        alias.name,
                    )
                continue

            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]

            value = getattr(node, "value", None)
            if (
                isinstance(value, ast.Call)
                and cls._called_name(value) == cls.NAMESPACE_CLASS
                and value.args
            ):
                value = value.args[0]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    constants[target.id] = value.value
                elif isinstance(value, ast.Call):
                    calls[target.id] = value

        return constants, calls, imports

    @staticmethod
    def _import_source(
        filename: Path, module: Optional[str], level: int
    ) -> Optional[Path]:
        """
        The file an ``from module import ...`` refers to, found on disk.

        A relative import resolves against the importing file. An absolute one
        is matched against the file's parent directories, so it resolves whether
        or not the project is on ``sys.path`` -- during a build it is not yet.
        """
        parts = module.split(".") if module else []
        roots = list(filename.parents)
        if level:
            # A relative import names one directory: one dot is the importing
            # file's own, each further dot one higher. Slicing rather than
            # indexing keeps a dot count past the filesystem root harmless.
            roots = roots[level - 1 : level]

        for root in roots:
            candidate = root.joinpath(*parts)
            for path in (candidate.with_suffix(".py"), candidate / "__init__.py"):
                if path.is_file():
                    return path
        return None

    def _lookup(
        self, name: str, filename: Path, bindings: Tuple[dict, dict, dict]
    ) -> Optional[Tuple[Any, Path, Tuple[dict, dict, dict]]]:
        """
        Follow ``NAME`` through ``from x import NAME`` until it is bound.

        Returns the string or call node it is bound to, with the file and the
        bindings it was found in, so a call node can be read in its own
        module. Each hop reads one more file, and a file already read ends the
        walk, so a re-export chain terminates and an import cycle does too.
        """
        seen: set = set()
        while True:
            constants, calls, imports = bindings
            if name in constants:
                return constants[name], filename, bindings
            if name in calls:
                return calls[name], filename, bindings
            if name not in imports:
                return None

            module, level, name = imports[name]
            source = self._import_source(filename, module, level)
            if source is None or source in seen:
                return None
            seen.add(source)

            filename = source
            with source.open("r") as f:
                bindings = self._bindings(ast.parse(f.read(), source))

    def _namespace(
        self, value: ast.AST, filename: Path, bindings: Tuple[dict, dict, dict]
    ) -> Optional[str]:
        """A namespace expression's value, if it is a string we can read statically."""
        if isinstance(value, ast.Constant):
            return value.value if isinstance(value.value, str) else None
        if isinstance(value, ast.Name):
            found = self._lookup(value.id, filename, bindings)
            if found is not None and isinstance(found[0], str):
                return found[0]
        return None

    def _key_namespace(
        self, value: ast.AST, filename: Path, bindings: Tuple[dict, dict, dict]
    ) -> Optional[str]:
        """The namespace of a key expression, if we can read it statically.

        The key is a ``NAMESPACE.key(...)`` or ``RegistrationKey(...)`` call,
        either written in place or bound to a name that is followed first.
        """
        if isinstance(value, ast.Name):
            found = self._lookup(value.id, filename, bindings)
            if found is None:
                return None
            value, filename, bindings = found
        if not isinstance(value, ast.Call):
            return None

        function = value.func
        if (
            isinstance(function, ast.Attribute)
            and function.attr == self.KEY_METHOD
            and isinstance(function.value, ast.Name)
        ):
            return self._namespace(function.value, filename, bindings)
        if self._called_name(value) == self.KEY_CLASS:
            for keyword in value.keywords:
                if keyword.arg == "namespace":
                    return self._namespace(keyword.value, filename, bindings)
        return None

    def _keyword(self, node: ast.Call, name: str) -> Optional[ast.AST]:
        for keyword in node.keywords:
            if keyword.arg == name:
                return keyword.value
        return None

    def _registered_namespace(self, node: ast.Call) -> None:
        """Record what a registration names, through ``namespace=`` or ``key=``."""
        bindings = (self._constants, self._calls, self._imports)
        namespace = self._keyword(node, "namespace")
        key = self._keyword(node, "key")
        found = None
        if namespace is not None:
            found = self._namespace(namespace, self._filename, bindings)
        elif key is not None:
            found = self._key_namespace(key, self._filename, bindings)
        if found is not None:
            self.namespaces.append(found)

    @staticmethod
    def _called_name(node: ast.AST) -> Optional[str]:
        """The bare name of what a decorator or call refers to."""
        target = node.func if isinstance(node, ast.Call) else node
        if isinstance(target, ast.Name):
            return target.id
        if isinstance(target, ast.Attribute):
            return target.attr
        return None

    def visit_FunctionDef(self, node):
        # Saved and restored so the flag describes *this* function only, rather
        # than everything the visitor happens to reach afterwards.
        previous_flag = self.register_flag
        self.register_flag = False

        for decorator in node.decorator_list:
            name = self._called_name(decorator)

            if name == self.REGISTER_METHOD_DECORATOR and isinstance(
                decorator, ast.Call
            ):
                self._registered_namespace(decorator)
                break

            if name == self.REGISTER_DECORATOR:
                self.register_flag = True
                break

        self.generic_visit(node)
        self.register_flag = previous_flag

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        # ``register_class`` puts the registration on the class rather than on
        # a method of it, so the namespace is read here. Without this a
        # directory whose configurations all use the class decorator scans as
        # registering no namespace at all, and every key referring into it from
        # another directory fails to resolve.
        for decorator in node.decorator_list:
            if self._called_name(decorator) == self.REGISTER_CLASS_DECORATOR and (
                isinstance(decorator, ast.Call)
            ):
                self._registered_namespace(decorator)
                break

        self.generic_visit(node)

    def visit_Call(self, node):
        # Only registration calls carry a namespace. Reading every call with
        # keywords meant a Param(description=...) inside a @register function
        # raised IndexError on the missing namespace.
        if self.register_flag and self._called_name(node) in self.REGISTRATION_CALLS:
            self._registered_namespace(node)
        self.generic_visit(node)


def match_name(name: str, names: Optional[Union[List[str], str]] = None):
    if names is None:
        return True

    names = names if isinstance(names, list) else [names]

    return name in names


def match_namespace(namespace: str, namespaces: Optional[Union[List[str], str]] = None):
    if namespaces is None:
        return True

    namespaces = namespaces if isinstance(namespaces, list) else [namespaces]

    return namespace in namespaces


def match_tags(a_tags: AbstractSet[str], b_tags: Tags) -> bool:
    if b_tags is None:
        return True

    if not len(a_tags) and None in b_tags:
        return True

    if len(a_tags) and None in b_tags:
        b_tags = b_tags - {None}

    if not len(b_tags - a_tags):
        return True

    return False


def import_class_from_string(path: str) -> type:
    """
    Import the class named by a dotted *path*.

    The split between module and attribute is found by trying the longest
    importable prefix, rather than assuming the last segment is the class.
    A nested class -- ``pkg.module.Outer.Inner`` -- has two attribute segments,
    and splitting once would try to import ``pkg.module.Outer``.
    """
    segments = path.split(".")
    for split in range(len(segments) - 1, 0, -1):
        module_path = ".".join(segments[:split])
        try:
            target: Any = importlib.import_module(module_path)
        except ModuleNotFoundError as error:
            if error.name == module_path or (
                error.name is not None and module_path.startswith(f"{error.name}.")
            ):
                continue
            raise
        for attribute in segments[split:]:
            target = getattr(target, attribute)
        return target

    # Nothing was importable: re-raise the failure for the natural split, whose
    # message names the module the caller most likely meant.
    return getattr(importlib.import_module(".".join(segments[:-1])), segments[-1])


def locate_module(module_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Find a module's source file **without importing anything**.

    Returns ``(origin, missing_segment)``: the file backing *module_path*, and
    the first dotted segment that could not be found.

    **Presence is signalled by** ``missing_segment is None``, not by ``origin``.
    A namespace package -- a directory with no ``__init__.py`` -- resolves
    successfully and yet has no file of its own, so it comes back as
    ``(None, None)``.

    ``importlib.util.find_spec`` cannot be used for this. Resolving a dotted
    path there imports the parent packages to read their ``__path__`` -- for
    ``sklearn.svm`` that costs 619 ms against 0.11 ms here, near enough the full
    import it was meant to avoid. Walking segment by segment and threading each
    package's ``submodule_search_locations`` into the next lookup keeps
    ``PathFinder`` on the filesystem, where it never executes module code.
    """
    search: Optional[List[str]] = None
    origin: Optional[str] = None
    segments = module_path.split(".")

    for index, segment in enumerate(segments):
        try:
            spec = PathFinder.find_spec(segment, search)
        except (ImportError, ValueError):  # pragma: no cover - odd path entries
            spec = None

        if spec is None:
            return None, ".".join(module_path.split(".")[: index + 1])

        origin = spec.origin
        if spec.submodule_search_locations is None:
            # A plain module: nothing further can be nested inside it. Passing
            # ``None`` back to PathFinder would restart at sys.path and could
            # mistake an unrelated top-level module for this module's child.
            if index < len(segments) - 1:
                return None, ".".join(segments[: index + 2])
            search = None
        else:
            search = list(spec.submodule_search_locations)

    return origin, None
