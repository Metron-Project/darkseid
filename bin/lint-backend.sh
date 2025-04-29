#!/bin/bash
# Lint checks
set -euxo pipefail

####################
###### Python ######
####################
uv run ruff check .
uv run ruff format --check .
# uv run pyright
uv run vulture .

############################################
##### Javascript, JSON, Markdown, YAML #####
############################################
npm run lint
