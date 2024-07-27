#!/bin/bash

# Base directories
mkdir -p data
mkdir -p data/{labeled_data,recordings,live}
mkdir -p data/live/{raw_data,jumps,processed_data}

# Subdirectories within labeled_data
cd data/labeled_data
mkdir -p axel/{double,quad,single,triple}
mkdir -p flip/{double,quad,single,triple}
mkdir -p loop/{double,quad,single,triple}
mkdir -p lutz/{double,quad,single,triple}
mkdir -p salchow/{double,quad,single,triple}
mkdir -p toe/{double,quad,single,triple}

echo "Directory structure has been set up."

