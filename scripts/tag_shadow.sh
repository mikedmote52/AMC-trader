#!/usr/bin/env bash
set -euo pipefail
TAG="${1:-v0.1-shadow}"
git fetch origin
git checkout main
git pull --rebase
git tag -a "$TAG" -m "UI live, Docker cron running, shadow mode"
git push origin "$TAG"
echo "Tagged and pushed $TAG"