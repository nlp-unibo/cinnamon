"""Run the study against the library, as a downstream project's entry point does.

python examples/downstream/run.py
"""

import sys
from pathlib import Path

from cinnamon import Registry

HERE = Path(__file__).resolve().parent
# Both projects import as ``downstream.*``, as if installed. Run as a script,
# only this file's own directory is on the path.
sys.path.insert(0, str(HERE.parent))


def main() -> None:
    from downstream.study.configurations.keys import TASK

    _, invalid = Registry.build(
        directory=HERE / "study", external_directories=[HERE / "library"]
    )
    if invalid:
        raise SystemExit(f"invalid registrations: {sorted(map(str, invalid))}")
    print(Registry.from_key(TASK).run())


if __name__ == "__main__":
    main()
