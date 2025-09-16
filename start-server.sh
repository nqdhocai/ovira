#!/bin/bash

# Exit on error
set -e

# Change to coral-server directory
cd coral-server

# Set config path and run gradlew
CONFIG_PATH="../" ./gradlew run --args="--sse-server 24145"
