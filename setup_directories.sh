#!/bin/bash

# Base directories
mkdir -p data
mkdir -p data/{labeled_data,recordings,live}
mkdir -p data/live/{raw_data,jumps,processed_data}

# Subdirectories within labeled_data
cd data/labeled_data

echo "Directory structure has been set up."

