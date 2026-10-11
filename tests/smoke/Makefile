# Makefile for VM Smoke Tests
# Use this to run specific provider smoke tests easily.

.PHONY: all multipass lima chameleon jetstream vbox wsl2 clean

# Default target: run all smoke tests
all:
	python3 -m pytest -s -vv tests/smoke

# Run Multipass smoke tests
multipass:
	OS_CLOUD=multipass python3 -m pytest -s -vv test-multipass-cli.py test_lifecycle_unified.py

# Run Lima smoke tests
lima:
	OS_CLOUD=lima python3 -m pytest -s -vv test-lima-cli.py test_lifecycle_unified.py

# Run Chameleon smoke tests
chameleon:
	OS_CLOUD=chameleon python3 -m pytest -s -vv test-chameleon-cli.py test-chameleon-smoke.py test_lifecycle_unified.py

# Run Jetstream smoke tests
jetstream:
	OS_CLOUD=jetstream python3 -m pytest -s -vv test-jetstream-cli.py test_lifecycle_unified.py

# Run VirtualBox smoke tests
vbox:
	OS_CLOUD=vbox python3 -m pytest -s -vv test-vbox-cli.py test_lifecycle_unified.py

# Run WSL2 smoke tests
wsl2:
	OS_CLOUD=wsl2 python3 -m pytest -s -vv test-wsl2-cli.py test_lifecycle_unified.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
