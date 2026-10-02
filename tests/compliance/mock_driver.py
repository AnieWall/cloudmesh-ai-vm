from typing import List, Optional

class MockNode:
    def __init__(self, name="mock-node", node_id="mock-id"):
        self.name = name
        self.id = node_id
        self.state = "RUNNING"
        self.public_ips = ["1.2.3.4"]
        self.ram = 2048
        self.cpus = 2

    def stop(self):
        """Stop the node."""
        pass

    def destroy(self):
        """Destroy the node."""
        pass

class MockImage:
    def __init__(self, name="mock-image", image_id="mock-img-id"):
        self.name = name
        self.id = image_id

class MockSize:
    def __init__(self, name="mock-size", size_id="mock-size-id"):
        self.name = name
        self.id = size_id
        self.ram = 2048
        self.vcpus = 2

class MockDriver:
    """
    A mock driver that implements the libcloud interface used by LibcloudManager.
    """
    def list_nodes(self) -> List[MockNode]:
        return []

    def get_node(self, name: str) -> Optional[MockNode]:
        return None

    def list_images(self) -> List[MockImage]:
        return []

    def list_sizes(self) -> List[MockSize]:
        return []

    def create_node(self, name, image, size) -> MockNode:
        return MockNode(name=name)

    def stop_node(self, node):
        pass

    def destroy_node(self, node):
        pass

    def reboot_node(self, node):
        pass

    def suspend_node(self, node):
        pass

    def shelve_node(self, node):
        pass

    def unshelve_node(self, node):
        pass

class MockDriverFactory:
    """
    Factory for creating MockDriver instances.
    """
    @staticmethod
    def get_driver() -> MockDriver:
        return MockDriver()
