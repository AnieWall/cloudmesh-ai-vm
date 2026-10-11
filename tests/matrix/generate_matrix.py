import json
import getpass
from datetime import datetime
from rich.console import Console
from rich.table import Table

from cloudmesh.ai.vm.aws.AwsManager import Provider as AwsManager
from cloudmesh.ai.vm.azure.AzureManager import Provider as AzureManager
from cloudmesh.ai.vm.google.GoogleManager import Provider as GoogleManager
from cloudmesh.ai.vm.oracle.OracleManager import Provider as OracleManager
from cloudmesh.ai.vm.openstack.OpenstackManager import OpenstackManager
from cloudmesh.ai.vm.openstack.JetstreamManager import Provider as JetstreamManager
from cloudmesh.ai.vm.openstack.ChameleonManager import Provider as ChameleonManager
from cloudmesh.ai.vm.local.MultipassManager import Provider as MultipassManager
from cloudmesh.ai.vm.local.VBoxManager import Provider as VBoxManager
from cloudmesh.ai.vm.local.LimaManager import Provider as LimaManager
from cloudmesh.ai.vm.local.Wsl2Manager import Provider as Wsl2Manager

from tests.matrix.base import MatrixTestBase

PROVIDERS = {
    "AWS": (AwsManager, {"clouds": {"aws": {}}}),
    "Azure": (AzureManager, {"clouds": {"azure": {}}}),
    "Google": (GoogleManager, {"clouds": {"google": {}}}),
    "Oracle": (OracleManager, {"clouds": {"oracle": {}}}),
    "OpenStack": (OpenstackManager, {"clouds": {"openstack": {}}}),
    "Jetstream": (JetstreamManager, {"clouds": {"jetstream": {}}}),
    "Chameleon": (ChameleonManager, {"clouds": {"chameleon": {}}}),
    "Multipass": (MultipassManager, {"clouds": {"multipass": {}}}),
    "VBox": (VBoxManager, {"clouds": {"vbox": {}}}),
    "Lima": (LimaManager, {"clouds": {"lima": {}}}),
    "WSL2": (Wsl2Manager, {"clouds": {"wsl2": {}}}),
}

def generate_matrix():
    console = Console()
    all_results = {}

    console.print("[bold blue]Probing VM Provider Capabilities...[/bold blue]\n")

    for name, (cls, config) in PROVIDERS.items():
        try:
            tester = MatrixTestBase(cls, config)
            all_results[name] = tester.probe_all()
            console.print(f"[green]✓[/green] {name} probed.")
        except Exception as e:
            console.print(f"[red]✗[/red] {name} failed: {e}")
            all_results[name] = {cap: "Broken" for cap in MatrixTestBase.CAPABILITIES}

    # Save JSON result
    MatrixTestBase.save_results(all_results)
    console.print(f"\n[bold]Results saved to tests/matrix/matrix_results.json[/bold]")

    # Generate Rich Table
    # Rows: Capabilities, Columns: Clouds
    table = Table(title="VM Provider Capability Matrix")

    # Columns are the clouds
    table.add_column("Capability", style="cyan")
    for cloud in PROVIDERS.keys():
        table.add_column(cloud, justify="center")

    # Rows are the capabilities
    for cap in MatrixTestBase.CAPABILITIES:
        row = [cap]
        for cloud in PROVIDERS.keys():
            status = all_results.get(cloud, {}).get(cap, "Unknown")

            if status == "Implemented":
                val = "[green]✅[/green]"
            elif status == "NotSupported":
                val = "[red]❌[/red]"
            elif status == "Broken":
                val = "[yellow]⚠️[/yellow]"
            else:
                val = "[grey]❓[/grey]"

            row.append(val)
        table.add_row(*row)

    console.print("\n")
    console.print(table)

if __name__ == "__main__":
    generate_matrix()
