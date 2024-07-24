#!/bin/bash

# Function to clear directory
clear_directory() {
    local dir=$1
    if [ -d "$dir" ]; then
        rm -rf ${dir}/*
        echo "Directory '$dir' exists. Contents cleared."
    else
        mkdir $dir
        echo "Directory '$dir' created."
    fi
}

# List of directories to always clear
directories=("raw_data" "processed_data" "jumps")

# Clear the specified directories
for dir in ${directories[@]}; do
    clear_directory $dir
done

