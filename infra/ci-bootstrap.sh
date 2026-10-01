#!/usr/bin/env bash
# Install the repository-declared hook before running governed checks.
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
test -x .githooks/pre-commit
git config --local core.hooksPath .githooks
# Keep the caller's argument boundaries and run the requested governed check.
if (( $# )); then
  exec "$@"
fi
