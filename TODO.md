# TODO-TUESDAY: VM Framework Enhancements

## 🔴 High Priority (Correctness & Stability)
- [ ] **Standardize State Polling**: Implement a `wait_for_status(vm_name, target_status, timeout)` method in `BaseVMProvider` and implement it in OpenStack/Multipass to prevent "race conditions" during start/stop.
- [ ] **Implement `get_provider_info`**: Ensure every manager implements this so the `cmx vm provider get` command returns useful version/status data instead of a generic error.
- [ ] **Batch CLI Commands**: Update `delete.py`, `stop.py`, and `restart.py` to accept multiple VM names or an `--all` flag.

## 🟡 Medium Priority (Feature Parity)
- [ ] **Expand Security Group Support**: Implement `create_security_group` and `add_security_group_rule` for Azure and Google providers.
- [ ] **Region Discovery**: Implement `list_regions` for all cloud-based providers to allow users to switch regions via CLI.
- [ ] **Key Rotation**: Add `rotate_key` to `BaseVMProvider` and implement it for providers that support SSH key updates.

## 🟢 Low Priority (UX & Polish)
- [ ] **Interactive VM Console**: Implement a `console` command to attach to a VM's serial console where supported (e.g., Multipass, OpenStack).
- [ ] **Enhanced Cost Templates**: Replace the `.md` cost templates with a structured JSON/YAML format that can be parsed by the `get_cost` method for real-time estimation.
- [ ] **Unified IP Abstraction**: Create a `NetworkInterface` class to handle the differences between Floating IPs, Public IPs, and Internal IPs across providers.
