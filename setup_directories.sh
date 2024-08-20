#!/bin/bash

# Base directories
mkdir -p data
mkdir -p data/{labeled_data,recordings,live,generated_data}
mkdir -p data/live/{raw_data,jumps,processed_data}

# Subdirectories within labeled_data
cd data/labeled_data
mkdir -p {axel,flip,loop,lutz,salchow,toe}
cd ../generated_data
mkdir -p {axel,flip,loop,lutz,salchow,toe}

echo "Directory structure has been set up."

