#!/bin/sh

PYTHONPATH="$(dirname "$0")" python3 -m netkit_python.install "$@"
