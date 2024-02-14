# todo find a way to build all images?
# then call this from some github workflow and have them registered

@PHONY: build

build:
	@echo "building all images as described in local docker-compose.yml"
	@docker compose build 