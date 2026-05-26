#!/bin/bash
set -e
cd "$(dirname "$0")/.."
SAILLY_TEST_MODE=1 python -m server.tests.regression.harness "$@"
