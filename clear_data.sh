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

