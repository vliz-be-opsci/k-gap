TIME_TAG=$(shell date +%s) # unix epoch
BUILD_TAG?=${TIME_TAG}     # provide the BUILD_TAG in the environment, or fallback to time
REG_NS?=kgap               # allow the namespace to be overridden to e.g. ghrc.io/vliz-be-opsci/kgap

@PHONY: build 

# usage `make BUILD_TAG=0.2 build` to include a specific tag to the build docker images
build:
	@export BUILD_TAG REG_NS
	@echo "building all images as described in local docker-compose.yml with tag ${BUILD_TAG}"
	@docker compose build --no-cache