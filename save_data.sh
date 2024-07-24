#!/bin/bash

# Directory where the recordings will be stored
base_dir="data/recordings"

# Find the lowest unused number for new directory
function find_lowest_unused_number {
    local i=0
    while true; do
        if [ ! -d "$base_dir/recording_$i" ]; then
            echo $i
            return
        fi
        ((i++))
    done
}

# Get the lowest unused number
number=$(find_lowest_unused_number)

# Create new directory with the lowest unused number
new_dir="$base_dir/recording_$number"
mkdir "$new_dir"

# Copy directories into the new directory
cp -r jumps "$new_dir/jumps"
cp -r raw_data "$new_dir/raw_data"
cp -r processed_data "$new_dir/processed_data"

echo "Created and set up directory $new_dir"

