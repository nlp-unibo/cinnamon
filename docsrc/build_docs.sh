#!/bin/bash
set -euo pipefail

# Build into docsrc/build/html and stop there. The output used to be copied into
# a tracked ../docs/ directory, which GitHub Pages then overwrote on every deploy
# anyway -- 38 generated files in git that were never actually served.
#
# -W turns warnings into errors. A removed module still listed in an automodule
# directive, or a broken cross-reference, then fails the build instead of
# quietly publishing a page that documents something which no longer exists.
#
# sphinx.ext.githubpages writes the .nojekyll that Pages needs to serve the
# _static directory.
sphinx-build -b html -W --keep-going source build/html
