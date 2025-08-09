# Makefile for MCP Inspector Tests

.PHONY: help install test test-single test-multi test-latest test-all clean inspector env-up env-down

# Default Docker version
DOCKER_VERSION ?= stable

help:
	@echo "MCP Inspector Test Commands:"
	@echo "  make install      - Install npm dependencies"
	@echo "  make test         - Run all tests"
	@echo "  make test-single  - Test single registry mode"
	@echo "  make test-multi   - Test multi-registry mode"  
	@echo "  make test-latest  - Test with :latest Docker tag"
	@echo "  make inspector    - Launch interactive Inspector UI"
	@echo "  make env-up       - Start test environment"
	@echo "  make env-down     - Stop test environment"
	@echo "  make clean        - Clean up everything"
	@echo ""
	@echo "Options:"
	@echo "  DOCKER_VERSION=<version>  - Specify Docker image version (default: stable)"
	@echo "  SKIP_ENV_SETUP=true      - Skip environment setup"
	@echo "  CLEANUP_AFTER=false      - Keep environment running after tests"

install:
	npm install

test: test-all

test-all:
	./run-inspector-tests.sh

test-single:
	DOCKER_VERSION=$(DOCKER_VERSION) ./run-inspector-tests.sh single

test-multi:
	DOCKER_VERSION=$(DOCKER_VERSION) ./run-inspector-tests.sh multi

test-latest:
	DOCKER_VERSION=latest ./run-inspector-tests.sh

inspector:
	npx @mcpjam/inspector

inspector-stable:
	npx @mcpjam/inspector --config ./config/inspector-config-stable.json

inspector-multi:
	npx @mcpjam/inspector --config ./config/inspector-config-multi.json

env-up:
	cd ../tests && ./start_test_environment.sh multi

env-down:
	cd ../tests && ./stop_test_environment.sh clean

clean: env-down
	rm -rf node_modules
	rm -f package-lock.json
	rm -f *.log

# Test specific Docker versions
test-v1.4.0:
	DOCKER_VERSION=v1.4.0 ./run-inspector-tests.sh

test-v1.3.0:
	DOCKER_VERSION=v1.3.0 ./run-inspector-tests.sh

# Development helpers
build-local:
	cd .. && docker build -t kafka-schema-reg-mcp:local .

test-local: build-local
	DOCKER_VERSION=local ./run-inspector-tests.sh

# CI simulation
ci-test:
	SKIP_ENV_SETUP=false CLEANUP_AFTER=true ./run-inspector-tests.sh
