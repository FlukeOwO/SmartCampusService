"""
Architecture diagram as code (official GCP icons via the `diagrams` library)

    pip install diagrams==0.24.4   # also needs Graphviz: apt install graphviz / brew install graphviz
    python docs/architecture/diagram.py

Outputs architecture.png and cicd.png next to this file.
Follows the course diagram standard: official provider icons, nested trust boundaries
(Provider -> Region -> VPC -> Subnet) and every arrow labelled with protocol:port.
Note: the library has no Secret Manager / Artifact Registry icons, so the KMS and
Container Registry icons stand in for them (swap in draw.io if you need the exact ones).
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.gcp.compute import Run
from diagrams.gcp.database import SQL
from diagrams.gcp.devtools import ContainerRegistry
from diagrams.gcp.network import VPC
from diagrams.gcp.operations import Logging, Monitoring
from diagrams.gcp.security import KMS, Iam
from diagrams.gcp.storage import GCS
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import Users
from diagrams.onprem.vcs import Github

OUT = Path(__file__).resolve().parent
GRAPH = {"fontsize": "20", "pad": "0.4", "nodesep": "0.7", "ranksep": "1.1", "splines": "spline"}
NODE = {"fontsize": "13"}
EDGE = {"fontsize": "12"}


def label(text: str, color: str = "#444444", style: str = "solid") -> Edge:
    return Edge(label=text, color=color, style=style, fontcolor=color)


def architecture() -> None:
    with Diagram(
        "Smart Campus Service Platform - Cloud Architecture (GCP)",
        filename=str(OUT / "architecture"),
        show=False,
        direction="LR",
        graph_attr=GRAPH,
        node_attr=NODE,
        edge_attr=EDGE,
    ):
        users = Users("Students / Staff / Admin\n(web browser)")

        with Cluster("Google Cloud - project smart-campus-prod"):
            with Cluster("Region asia-southeast1 (Singapore) - multi-zone managed services"):
                web = GCS("campus-web bucket\n(public, React static files)")
                uploads = GCS("campus-uploads bucket\n(private, attachments)\nStandard>Nearline>Coldline")
                secrets = KMS("Secret Manager\ndb-password, jwt-secret-key")
                registry = ContainerRegistry("Artifact Registry\ncampus/api:<git-sha>")

                with Cluster("Cloud Run (serverless containers, autoscale 0-3)"):
                    api = Run("campus-api\nFastAPI (stateless)")
                    migrate = Run("campus-migrate job\nalembic upgrade head")

                with Cluster("VPC campus-vpc (custom mode)"):
                    with Cluster("Subnet campus-run-subnet 10.10.0.0/24\nDirect VPC Egress, private-ranges-only"):
                        egress = VPC("egress path")

                with Cluster("Private Services Access 10.20.0.0/20 (VPC peering)\nno public IP"):
                    db = SQL("Cloud SQL PostgreSQL 15\ncampus-db (private IP)")

                with Cluster("Operations"):
                    logs = Logging("Cloud Logging\n(JSON logs + trace)")
                    metrics = Monitoring("Cloud Monitoring\ndashboard + budget")

        users >> label("HTTPS:443  GET static files") >> web
        users >> label("HTTPS:443  REST API + JWT", "#1a73e8") >> api
        users << label("HTTPS:443  V4 Signed URL (15 min)", "#188038", "dashed") << uploads
        api >> label("VPC egress", "#5f6368") >> egress
        egress >> label("TCP:5432 (TLS)  SQL", "#d93025") >> db
        migrate >> label("TCP:5432 (TLS)", "#d93025", "dashed") >> egress
        api >> label("HTTPS:443  objects API (IAM SA)", "#188038") >> uploads
        api >> label("HTTPS:443  secrets at startup", "#9334e6", "dashed") >> secrets
        registry >> label("image pull", "#5f6368", "dashed") >> api
        api >> label("stdout logs / metrics", "#5f6368", "dotted") >> logs
        logs - Edge(style="invis") - metrics


def cicd() -> None:
    with Diagram(
        "Smart Campus - CI/CD (GitHub Actions -> Cloud Run, zero-downtime)",
        filename=str(OUT / "cicd"),
        show=False,
        direction="LR",
        graph_attr=GRAPH,
        node_attr=NODE,
        edge_attr=EDGE,
    ):
        repo = Github("GitHub repo\nPR -> dev -> main")
        with Cluster("GitHub Actions"):
            ci = GithubActions("backend-ci\nruff, pytest,\nmigrations, docker build")
            cd = GithubActions("backend-cd /\nfrontend-cd")
        with Cluster("Google Cloud"):
            wif = Iam("Workload Identity\nFederation (OIDC,\nno JSON key)")
            registry = ContainerRegistry("Artifact Registry")
            migrate = Run("1. migration job")
            new_rev = Run("2. new revision\n--no-traffic + tag")
            live = Run("3. smoke test /healthz\nthen 100% traffic\n(or canary %)")
            web = GCS("frontend bucket\n(gcloud storage rsync)")

        repo >> label("push / PR") >> ci
        ci >> label("merge to dev/main") >> cd
        cd >> label("OIDC token") >> wif
        cd >> label("docker push :git-sha") >> registry
        cd >> migrate >> new_rev >> live
        cd >> label("vite build") >> web


if __name__ == "__main__":
    architecture()
    cicd()
    print(f"wrote {OUT / 'architecture.png'} and {OUT / 'cicd.png'}")
