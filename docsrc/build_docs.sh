#!/bin/bash
set -euo pipefail

# -W turns warnings into errors. A removed module still listed in an automodule
# directive, or a broken cross-reference, then fails the build instead of
# quietly publishing a page that documents something which no longer exists.
sphinx-build -b html -W --keep-going source build/html

cp -r ./build/html/* ../docs/
