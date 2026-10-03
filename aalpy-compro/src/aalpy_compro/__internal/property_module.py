from collections.abc import Sequence
from importlib.util import module_from_spec, spec_from_file_location
from types import ModuleType


def load_property_module(
    path: str, *, module_name: str, required_attributes: Sequence[str]
) -> ModuleType:
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load property from {path}.")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    for name in required_attributes:
        if not hasattr(module, name):
            raise ValueError(f"`{name}` must be defined in {path}.")

    return module
