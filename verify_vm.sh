#!/usr/bin/env bash

# Verification script for cloudmesh-ai-vm.
#
# Demonstrates success or failure of VM CLI commands.
#
# Safe mode:
#   ./verify_vm.sh
#   ./verify_vm.sh <vm-name>
#
# Lifecycle mode (may modify cloud resources):
#   ./verify_vm.sh <vm-name> --lifecycle

VM_NAME="${1:-}"
MODE="${2:-}"
PASSED=0
FAILED=0
SKIPPED=0

run_test() {
    local description="$1"
    shift

    echo
    echo "============================================================"
    echo "TEST: $description"
    echo "COMMAND: $*"
    echo "------------------------------------------------------------"

    "$@"
    local status=$?

    if [[ $status -eq 0 ]]; then
        echo "[PASS] $description"
        PASSED=$((PASSED + 1))
    else
        echo "[FAIL] $description (exit code: $status)"
        FAILED=$((FAILED + 1))
    fi
}

skip_test() {
    echo
    echo "[SKIP] $1"
    SKIPPED=$((SKIPPED + 1))
}

echo "cloudmesh-ai-vm verification"
echo "============================"

#
# General CLI
#
run_test "VM CLI help" cmx vm --help

#
# Account and provider configuration
#
run_test "Account information" cmx vm account
run_test "Cloud provider list" cmx vm cloud list
run_test "Cloud provider get" cmx vm cloud get
run_test "Provider list" cmx vm provider list
run_test "Provider get" cmx vm provider get
run_test "Configuration list" cmx vm config list

#
# Images, flavors, and resources
#
run_test "List flavors" cmx vm flavor
run_test "List images" cmx vm image
run_test "List VMs" cmx vm list vms
run_test "List regions" cmx vm list regions

#
# SSH keys
#
run_test "List SSH keys" cmx vm key list

#
# Security groups
#
run_test "List security groups" cmx vm security-group list

#
# Provider-specific / UI command
#
run_test "Horizon command help" cmx vm horizon --help

#
# VM-specific commands
#
if [[ -n "$VM_NAME" ]]; then
    run_test "VM information" cmx vm info "$VM_NAME"
    run_test "VM login information" cmx vm login "$VM_NAME"
    run_test "SSH config generation" cmx vm ssh-config "$VM_NAME"

    # Avoid opening an interactive SSH session automatically.
    run_test "SSH command availability" cmx vm ssh --help

    # Demonstrate remote-command interface without modifying the VM.
    run_test "Remote command help" cmx vm run --help
else
    skip_test "VM info: no VM name supplied."
    skip_test "VM login: no VM name supplied."
    skip_test "SSH config: no VM name supplied."
    skip_test "SSH session: no VM name supplied."
    skip_test "Remote command: no VM name supplied."
fi

#
# Lifecycle commands
#
# These commands can modify cloud resources and therefore require explicit
# lifecycle mode and a dedicated test VM name.
#
if [[ "$MODE" == "--lifecycle" && -n "$VM_NAME" ]]; then
    echo
    echo "WARNING: lifecycle mode modifies VM state."
    echo "Test VM: $VM_NAME"

    run_test "Start VM" cmx vm start "$VM_NAME"
    run_test "Restart VM" cmx vm restart "$VM_NAME"
    run_test "Stop VM" cmx vm stop "$VM_NAME"
    run_test "Suspend VM" cmx vm suspend "$VM_NAME"
    run_test "Reset VM" cmx vm reset "$VM_NAME"

    # OpenStack-specific lifecycle operations may fail on other providers.
    run_test "Shelve VM" cmx vm shelve "$VM_NAME"
    run_test "Unshelve VM" cmx vm unshelve "$VM_NAME"

    # Delete is intentionally last.
    run_test "Delete VM" cmx vm delete "$VM_NAME"
else
    skip_test "start: lifecycle mode not enabled."
    skip_test "restart: lifecycle mode not enabled."
    skip_test "stop: lifecycle mode not enabled."
    skip_test "suspend: lifecycle mode not enabled."
    skip_test "reset: lifecycle mode not enabled."
    skip_test "shelve: lifecycle mode not enabled."
    skip_test "unshelve: lifecycle mode not enabled."
    skip_test "delete: lifecycle mode not enabled."
fi

echo
echo "============================================================"
echo "Verification summary"
echo "============================================================"
echo "Passed:  $PASSED"
echo "Failed:  $FAILED"
echo "Skipped: $SKIPPED"

if [[ "$FAILED" -gt 0 ]]; then
    exit 1
fi

exit 0