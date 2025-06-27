#!/bin/bash

# if basename is GrayGEMS, then clean the demo directory
if [ "$(basename "$PWD")" == "GrayGEMS" ]; then
    rm -rf demo/downloads/* demo/projects/* demo/test_results/*
else
    rm -rf downloads/* projects/* test_results/*
fi