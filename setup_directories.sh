#!/bin/bash

# Base directories
mkdir -p data jumps raw_data processed_data
mkdir -p data/labeled_data data/recordings

# Subdirectories within labeled_data
cd data/labeled_data
mkdir -p axel/{double,quad,single,triple}
mkdir -p flip/{double,quad,single,triple}
mkdir -p loop/{double,quad,single,triple}
mkdir -p lutz/{double,quad,single,triple}
mkdir -p salchow/{double,quad,single,triple}
mkdir -p toe/{double,quad,single,triple}

echo "Directory structure has been set up."

