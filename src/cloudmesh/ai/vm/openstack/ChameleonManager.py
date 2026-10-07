import yaml
from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager

try:
    import chi
except ImportError:
    # Mocking chi for environments where it is not installed
    class ChiMock:
        def use_site(self, site): pass
        def set(self, key, value): pass
        class Lease:
            def add_node_reservation(self, res, node_type, count): res.append({"node_type": node_type, "count": count})
            def lease_duration(self, days): return "start", "end"
            def create_lease(self, name, res, start_date, end_date): pass
        lease = Lease()
    chi = ChiMock()

class Provider(OpenstackManager):
    """
    Chameleon Cloud implementation of the OpenstackManager.
    """

    def _get_node_type(self, flavor: str) -> str:
        """
        Maps an OpenStack flavor name to a Chameleon node type.
        """
        cloud_config = self.get_cloud_config("chameleon")
        mapping = cloud_config.get("node_type_mapping", {
            "m1.small": "compute_haswell",
            "m1.medium": "compute_haswell",
            "m1.large": "compute_haswell",
        })
        return mapping.get(flavor, "compute_haswell")

    def start(self, name: Optional[str] = None, flavor: Optional[str] = None, image: Optional[str] = None, assign_ip: bool = True) -> str:
        """Starts a VM in Chameleon using libcloud, automatically creating a 1-hour reservation."""
        cloud_config = self.get_cloud_config("chameleon")
        image_name = image or cloud_config.get("image")
        flavor_name = flavor or cloud_config.get("flavor")
        security_group = cloud_config.get("security_group", "default")
        key_name = cloud_config.get("key_name")
        if not key_name and cloud_config.get("key_path"):
            key_name = Path(cloud_config["key_path"]).name.replace(".pub", "")

        if not image_name:
            raise ConfigError(f"Missing 'image' in config for {self.cloud_name}")
        if not flavor_name:
            raise ConfigError(f"Missing 'flavor' in config for {self.cloud_name}")

        try:
            # 1. Automatic Reservation for Chameleon
            node_type = self._get_node_type(flavor_name)
            vm_name = name or f"vm-{self.cloud_name}"
            if not name and self.cloud_name in ["jetstream", "chameleon"]:
                username = cloud_config.get("username", "user").replace("_", "-")
                site = cloud_config.get("site", self.cloud_name).replace("_", "-").replace("@", "").lower()
                vm_name = f"{vm_name}-{username}" if site == self.cloud_name else f"{vm_name}-{site}-{username}"

            res_name = f"res-{vm_name}"
            reservation_id = self.create_reservation(
                name=res_name,
                node_type=node_type,
                count=1,
                duration=1 # Default to 1 day for the reservation as per chi.lease.lease_duration
            )

            if not reservation_id:
                from cloudmesh.ai.vm.logger import logger
                logger.warning(f"Could not create automatic reservation for {vm_name}. Attempting to start without it...")

            # 2. Find image and flavor objects
            all_images = self.driver.list_images()
            img = next((i for i in all_images if i.name == image_name), None)
            if not img:
                raise VMResourceError(f"Could not find image {image_name} in {self.cloud_name}")

            all_flavors = self.driver.list_sizes()
            flv = next((f for f in all_flavors if f.name == flavor_name), None)
            if not flv:
                raise VMResourceError(f"Could not find flavor {flavor_name} in {self.cloud_name}")

            security_groups = self.driver.ex_list_security_groups()
            sg = next((group for group in security_groups if group.name == security_group), None)
            if sg is None:
                raise VMResourceError(f"Could not find security group {security_group} in {self.cloud_name}")

            # 3. Create node with reservation hint
            scheduler_hints = {}
            if reservation_id:
                scheduler_hints['reservation_id'] = reservation_id

            node = self.driver.create_node(
                name=vm_name,
                image=img,
                size=flv,
                ex_keyname=key_name,
                ex_security_groups=[sg],
                ex_scheduler_hints=scheduler_hints
            )

            if assign_ip:
                self.assign_floating_ip(vm_name)

            return node.id
        except Exception as e:
            from cloudmesh.ai.vm.logger import logger
            logger.error(f"Libcloud start failed for {self.cloud_name}: {e}")
            raise VMProviderError(f"Libcloud start failed for {self.cloud_name}: {e}") from e

    def list_regions(self) -> List[Dict[str, Any]]:
        """Lists available sites/regions in Chameleon Cloud."""
        try:
            sites_dict = chi.context.list_sites(show=None)
            regions = []
            for site_name, properties in sites_dict.items():
                regions.append({"name": site_name, **properties})
            return regions
        except Exception as e:
            self.print(f"Error listing Chameleon regions: {e}")
            return []

    def create_reservation(self, name: str, node_type: str, count: int, start_date: str = None, end_date: str = None, duration: int = None) -> Optional[str]:
        """
        Creates a node reservation (lease) in Chameleon Cloud using python-chi.
        Returns the reservation ID if successful, None otherwise.
        """
        cloud_config = self.get_cloud_config("chameleon")
        site = cloud_config.get("site", "CHI@TACC")
        project = cloud_config.get("project_name")

        if not project:
            self.print("Error: 'project_name' must be configured in clouds.yaml for Chameleon reservations.")
            return None

        try:
            # Configure chi
            chi.use_site(site)
            chi.set("project_name", project)

            reservations = []
            chi.lease.add_node_reservation(
                reservations,
                node_type=node_type,
                count=count,
            )

            # Determine start and end dates
            if duration:
                s, e = chi.lease.lease_duration(days=duration)
            elif start_date and end_date:
                s, e = start_date, end_date
            else:
                s, e = chi.lease.lease_duration(days=1)

            lease = chi.lease.create_lease(
                name,
                reservations,
                start_date=s,
                end_date=e,
            )
            return lease.get('id') if isinstance(lease, dict) else getattr(lease, 'id', None)
        except Exception as e:
            self.print(f"Error creating reservation in Chameleon: {e}")
            return None


    def get_account_info(self) -> Dict[str, Any]:
        """Returns account information for Chameleon using chi."""
        try:
            cloud_config = self.get_cloud_config("chameleon")
            site = cloud_config.get("site", "CHI@TACC")
            project = cloud_config.get("project_name")
            
            if not project:
                return {"error": "'project_name' must be configured in clouds.yaml for Chameleon."}
            
            # Configure chi to ensure we are targeting the correct site and project
            chi.use_site(site)
            chi.set("project_name", project)
            
            return {
                "site": site,
                "project_name": project,
                "project_id": chi.get("project_id"),
                "user_id": chi.get("user_id"),
                "allocation": chi.get("allocation") if hasattr(chi, "get") else "Unknown"
            }
        except Exception as e:
            self.print(f"Error fetching Chameleon account info: {e}")
            return {"error": f"Failed to fetch Chameleon account info: {str(e)}"}

