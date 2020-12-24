#!/bin/bash

__tool=../../venv/bin/circuitpython-build-bundles

circuitpython-build-bundles --filename_prefix matriximagedecoder --library_location matriximagedecoder/

circuitpython-build-bundles --filename_prefix matrixserver --library_location matrixserver/
