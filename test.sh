#! /usr/bin/env bash
export TAG=0.0.1
#if [[ $TAG =~ ^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$ ]]; then 
if [[ $TAG =~ ^[0-9]+\.[0-9]+\.\d+$ ]]; then 
   export build_tag=$TAG 
else 
   export build_tag="latest" 
fi 

echo $build_tag