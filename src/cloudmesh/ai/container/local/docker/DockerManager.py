import docker
from typing import Any
from ....vm.CloudBaseManager import CloudBaseManager
from cloudmesh.ai.vm.exceptions import ProviderFeatureNotSupported
from cloudmesh.ai.vm.logger import logger


class DockerManager(CloudBaseManager):
    """Manages Docker containers using the docker‑py library."""

    def __init__(self, config: Any, cloud_name: str = "docker", console=None, **kwargs):
        """Initialize the manager and Docker client.

        ``cloud_name`` defaults to ``docker`` for CLI compatibility. ``console``
        is passed to the base class. Additional ``kwargs`` are forwarded to the
        ``CloudBaseManager`` constructor.
        """
        super().__init__(config, console=console, **kwargs)
        self.cloud_name = cloud_name
        try:
            self.client = docker.from_env()
            logger.debug("Docker client initialized from environment.")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

    def list(self) -> list[dict[str, Any]]:
        """List all Docker containers (running and stopped)."""
        if not self.client:
            return []
        containers = self.client.containers.list(all=True)
        return [
            {
                "name": c.name,
                "id": c.id[:12],
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else "none",
            }
            for c in containers
        ]

    def start(
        self,
        name: str | None = None,
        flavor: str | None = None,
        image: str | None = None,
        dockerfile: str | None = None,
        network: str | None = None,
        cmd: str | None = None,
        **kwargs,
    ) -> str:
        """Start a container, creating it if it does not exist.

        ``dockerfile`` can be used to build an image before running. ``flavor``
        is ignored for Docker but retained for API compatibility.
        """
        if not self.client:
            raise ProviderFeatureNotSupported(self.cloud_name, "start")
        name = name or "docker-container"
        if self.exists(name):
            container = self.client.containers.get(name)
            container.start()
            return f"Container {name} started."
        if dockerfile:
            try:
                logger.info(f"Building image from Dockerfile: {dockerfile}")
                image_obj, _ = self.client.images.build(path=dockerfile)
                image = image_obj.tags[0] if image_obj.tags else "built-image"
            except Exception as e:
                raise ProviderFeatureNotSupported(
                    self.cloud_name,
                    f"build image from Dockerfile {dockerfile}: {e}",
                )
        else:
            image = image or "ubuntu:latest"
        container = self.client.containers.run(
            image,
            command=cmd,
            name=name,
            detach=True,
            network=network,
        )
        return f"Container {name} created and started from image {image}."

    def stop(self, name: str | None = None) -> bool:
        """Stop a Docker container."""
        if not self.client or not name:
            return False
        try:
            container = self.client.containers.get(name)
            container.stop()
            return True
        except Exception as e:
            logger.error(f"Error stopping container {name}: {e}")
            return False

    def restart(self, name: str | None = None) -> bool:
        """Restart a Docker container."""
        if not self.client or not name:
            return False
        try:
            container = self.client.containers.get(name)
            container.restart()
            return True
        except Exception as e:
            logger.error(f"Error restarting container {name}: {e}")
            return False

    def delete(self, name: str | None = None) -> bool:
        """Delete a Docker container."""
        if not self.client or not name:
            return False
        try:
            container = self.client.containers.get(name)
            container.remove(force=True)
            return True
        except Exception as e:
            logger.error(f"Error deleting container {name}: {e}")
            return False

    def info(self, name: str, kind: str = "vm") -> dict[str, Any]:
        """Return detailed information for a Docker container."""
        if not self.client:
            return {}
        try:
            container = self.client.containers.get(name)
            attrs = container.attrs
            ip = (
                attrs["NetworkSettings"]["IPAddress"]
                or next(
                    iter(attrs["NetworkSettings"]["Networks"].values()),
                    {},
                ).get("IPAddress", "N/A")
            )
            return {
                "name": attrs.get("Name"),
                "id": attrs.get("Id"),
                "status": attrs.get("State", {}).get("Status"),
                "image": attrs.get("Config", {}).get("Image"),
                "ip": ip,
            }
        except Exception as e:
            logger.error(f"Error getting info for container {name}: {e}")
            return {}

    def login(self, name: str | None = None) -> bool:
        """Execute an interactive shell inside the container."""
        if not self.client or not name:
            return False
        import subprocess
        try:
            subprocess.run(["docker", "exec", "-it", name, "/bin/bash"], check=True)
            return True
        except Exception as e:
            logger.error(f"Error logging into container {name}: {e}")
            return False

    def run_command(self, name: str, cmd: str) -> str:
        """Run a command inside the container and return its output."""
        if not self.client:
            return "Docker client not available"
        try:
            container = self.client.containers.get(name)
            result = container.exec_run(cmd)
            return result.output.decode("utf-8")
        except Exception as e:
            return f"Error running command: {e}"

    def pause(self, name: str) -> bool:
        """Pause a Docker container."""
        if not self.client or not name:
            return False
        try:
            container = self.client.containers.get(name)
            container.pause()
            return True
        except Exception as e:
            logger.error(f"Error pausing container {name}: {e}")
            return False

    def unpause(self, name: str) -> bool:
        """Unpause a Docker container."""
        if not self.client or not name:
            return False
        try:
            container = self.client.containers.get(name)
            container.unpause()
            return True
        except Exception as e:
            logger.error(f"Error unpausing container {name}: {e}")
            return False

    def list_images(self) -> list[dict[str, Any]]:
        """List Docker images."""
        if not self.client:
            return []
        try:
            images = self.client.images.list()
            return [{"id": img.id, "tags": img.tags} for img in images]
        except Exception as e:
            logger.error(f"Error listing images: {e}")
            return []

    def pull_image(self, image: str) -> bool:
        """Pull a Docker image."""
        if not self.client:
            return False
        try:
            self.client.images.pull(image)
            return True
        except Exception as e:
            logger.error(f"Error pulling image {image}: {e}")
            return False

    def delete_image(self, image_id: str) -> bool:
        """Delete a Docker image."""
        if not self.client:
            return False
        try:
            self.client.images.remove(image=image_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting image {image_id}: {e}")
            return False

    def get_container_ip(self, name: str) -> str | None:
        """Get the IP address of a container."""
        if not self.client:
            return None
        try:
            container = self.client.containers.get(name)
            networks = container.attrs["NetworkSettings"]["Networks"]
            if networks:
                first_net = list(networks.values())[0]
                return first_net.get("IPAddress")
        except Exception as e:
            logger.error(f"Error getting IP for container {name}: {e}")
        return None

    def list_container_ips(self) -> list[dict[str, str]]:
        """List IPs for all running containers."""
        if not self.client:
            return []
        containers = self.client.containers.list()
        return [
            {"name": c.name, "ip": self.get_container_ip(c.name) or "N/A"}
            for c in containers
        ]

    def create_network(self, name: str) -> bool:
        """Create a Docker network."""
        if not self.client:
            return False
        try:
            self.client.networks.create(name, driver="bridge")
            return True
        except Exception as e:
            logger.error(f"Error creating network {name}: {e}")
            return False

    def list_networks(self) -> list[dict[str, Any]]:
        """List all Docker networks."""
        if not self.client:
            return []
        try:
            networks = self.client.networks.list()
            return [{"name": n.name, "id": n.id} for n in networks]
        except Exception as e:
            logger.error(f"Error listing networks: {e}")
            return []

    def delete_network(self, name: str) -> bool:
        """Delete a Docker network."""
        if not self.client or not name:
            return False
        try:
            network = self.client.networks.get(name)
            network.remove()
            return True
        except Exception as e:
            logger.error(f"Error deleting network {name}: {e}")
            return False

# Compatibility alias
Docker = DockerManager