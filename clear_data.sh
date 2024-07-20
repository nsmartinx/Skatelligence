#!/bin/bash

# Check if the directory 'data' exists in the current directory
if [ -d "data" ]; then
    # If the directory exists, clear its contents
    rm -rf data/*
    echo "Directory 'data' exists. Contents cleared."
else
    # If the directory does not exist, create it
    mkdir data
    echo "Directory 'data' created."
fi

# Check if the directory 'processed_data' exists in the current directory
if [ -d "processed_data" ]; then
    # If the directory exists, clear its contents
    rm -rf processed_data/*
    echo "Directory 'processed_data' exists. Contents cleared."
else
    # If the directory does not exist, create it
    mkdir processed_data
    echo "Directory 'processed_data' created."
fi

# Check if the directory 'processed_data' exists in the current directory
if [ -d "jumps" ]; then
    # If the directory exists, clear its contents
    rm -rf jumps/*
    echo "Directory 'jumps' exists. Contents cleared."
else
    # If the directory does not exist, create it
    mkdir jumps
    echo "Directory 'jumps' created."
fi

