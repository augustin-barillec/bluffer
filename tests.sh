#!/bin/bash

export PYTHONPATH=$(pwd)

pytest tests/unit/slash_command.py
