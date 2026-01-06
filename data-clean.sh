#!/bin/bash

for d in "graphdb-import" "graphdb" "ldes-consumer"; do
    rm -rf ./data/$d/*
done