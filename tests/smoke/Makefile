# Makefile for VM Smoke Tests
# Use this to run specific provider smoke tests easily.

.PHONY: all multipass lima chameleon jetstream vbox wsl2 clean help

.DEFAULT_GOAL := help

# Run all smoke tests
all: ## Run all smoke tests
	python3 -m pytest -s -vv tests/smoke

# Run Multipass smoke tests
multipass: ## Run Multipass smoke tests
	OS_CLOUD=multipass python3 -m pytest -s -vv test-multipass-cli.py "test_lifecycle_unified.py::test_provider_lifecycle[multipass]"

# Run Lima smoke tests
lima: ## Run Lima smoke tests
	OS_CLOUD=lima python3 -m pytest -s -vv test-lima-cli.py "test_lifecycle_unified.py::test_provider_lifecycle[lima]"

# Run Chameleon smoke tests
chameleon: ## Run Chameleon smoke tests
	# OS_CLOUD=chameleon python3 -m pytest -s -vv test-chameleon-cli.py test-chameleon-smoke.py "test_lifecycle_unified.py::test_provider_lifecycle[chameleon]"
	OS_CLOUD=chameleon python3 -m pytest -s -vv test-chameleon-cli.py "test_lifecycle_unified.py::test_provider_lifecycle[chameleon]"


# Run Jetstream smoke tests
jetstream: ## Run Jetstream smoke tests
	OS_CLOUD=jetstream python3 -m pytest -s -vv test-jetstream-cli.py "test_lifecycle_unified.py::test_provider_lifecycle[jetstream]"

# Run VirtualBox smoke tests
vbox: ## Run VirtualBox smoke tests
	OS_CLOUD=vbox python3 -m pytest -s -vv test-vbox-cli.py "test_lifecycle_unified.py::test_provider_lifecycle[vbox]"

# Run WSL2 smoke tests
wsl2: ## Run WSL2 smoke tests
	OS_CLOUD=wsl2 python3 -m pytest -s -vv test-wsl2-cli.py "test_lifecycle_unified.py::test_provider_lifecycle[wsl2]"

# Clean up cache files
clean: ## Remove all Python cache files (__pycache__)
	find . -type d -name "__pycache__" -exec rm -rf {} +

# Show help documentation
help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)