# Note: Ensure variable declarations in makefiles have NO trailing whitespace
#       This can be achieved by sliding in the # comment-sign directly after the value
PROJECT := "kgap"#              - this project
TIME_TAG := $(shell date +%s)#  - the unix epoch
BUILD_TAG ?= ${TIME_TAG}#       - provide the BUILD_TAG in the environment, or fallback to time
REG_NS ?= "kgap"#               - allow the namespace to be overridden to e.g. ghcr.io/vliz-be-opsci/kgap
DIMGS="graphdb jupyter"#        - the list of docker images in docker-compose.yml ready to be pushed

.PHONY: help docker-build docker-push docker-start docker-stop
.DEFAULT_GOAL := help


help:  ## Shows this list of available targets and their effect.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


# usage `make BUILD_TAG=0.2 docker-build` to include a specific tag to the build docker images
docker-build: ## Builds the docker-images as described in the local docker-compose.yml for ${REG_NS} and ${BUILD_TAG}
	@echo "building all images as described in local docker-compose.yml for registry/namespace=${REG_NS} with tag=${BUILD_TAG}"
	@env BUILD_TAG=${BUILD_TAG} REG_NS=${REG_NS} bash -c "docker compose build --no-cache"
	

# usage `make REG_NS=ghcr.io/vliz-be-opsci/kgap docker-build` to push images to github-container-registry
docker-push: docker-build ## Builds, then pushes the docker-images to ${REG_NS}
	@echo "pushing docker images tagged=${BUILD_TAG} to registry/namespace=${REG_NS}"
ifeq ($(shell echo ${REG_NS} | egrep '.+/.+'),)  # the 'shell' call is essential
# empty match indicates no registry-part is available to push to
	@echo "not pushing docker images if no / between non-empty parts in REG_NS=${REG_NS}"
	@exit 1
else
# note the double $$ on dn distinction between makefile and shell var expansion
	@for dn in "${DIMGS}"; do \
		docker push ${REG_NS}/${PROJECT}_$${dn}:${BUILD_TAG}; \
	done;
endif


docker-start:  ## Launches local-named variants of the containers/images in docker-compose.yml
	@echo "launching docker-stack for local test with default names and tags"
	@mkdir -p ./data/
	@mkdir -p ./notebooks/
	@docker compose -p ${PROJECT} up -d


docker-stop:  ## Stops local-named variants of those containers
	@echo "shutting down docker-stack from docker-start"
	@docker compose -p ${PROJECT} down


docker-clean:  ## Helps (interactively) to cleanup containers and images linked to this project
	@./docker_clean.sh ${PROJECT}
