from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, EKS
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB, APIGateway
from diagrams.aws.security import IAMRole
from diagrams.aws.management import Cloudformation
from diagrams.aws.devtools import Codecommit
from diagrams.onprem.iac import Terraform 
from diagrams.onprem.vcs import Git
from diagrams.k8s.compute import Pod
from diagrams.onprem.gitops import ArgoCD

graph_attr = {
    "pad": "0",
}

# Diagram 1: Everything managed by Terraform (including app deployments)
with Diagram(
    "1. All Managed by Terraform",
    show=False,
    filename="../blog/static/diagrams/eks-all-terraform",
    direction="TB",
    outformat="png",
    graph_attr=graph_attr
):
    tf_repo = Git("Terraform Codebase")
    terraform = Terraform("")
    aws_api = APIGateway("AWS API")

    with Cluster("AWS Account",):
        with Cluster("EKS"):
            eks = EKS("EKS Control Plane")
            nodegroups = EC2("Node Groups")
            podidentities = IAMRole("Pod Identities")
            with Cluster("Kubernetes"):
                app = Pod("App Deployment")

        iam = IAMRole("IAM Roles")
        rds = RDS("RDS")
        elb = ELB("Load Balancer")

    tf_repo >> terraform
    terraform >> aws_api
    aws_api >> [iam, rds, elb, eks, nodegroups, podidentities]
    terraform >> app

# Diagram 2: ArgoCD for Apps, Terraform for Infra
with Diagram(
    "2. ArgoCD for Apps, Terraform for Infra",
    show=False,
    filename="../blog/static/diagrams/eks-terraform-argo",
    direction="TB",
    outformat="png",
    graph_attr=graph_attr
):
    tf_repo = Git("Terraform Codebase")
    terraform = Terraform("")
    aws_api = APIGateway("AWS API")

    argo_repo = Git("GitOps Codebase")

    with Cluster("AWS Account"):
        with Cluster("EKS Cluster"):
            eks = EKS("EKS Control Plane")
            nodegroups = EC2("Node Groups")
            podidentities = IAMRole("Pod Identities")
            with Cluster("Kubernetes"):
                argocd = ArgoCD("ArgoCD")
                app = Pod("App Deployment")

        iam = IAMRole("IAM Roles")
        rds = RDS("RDS")
        elb = ELB("Load Balancer")

    tf_repo >> terraform
    terraform >> aws_api
    aws_api >> [iam, rds, elb, eks, nodegroups, podidentities]
    argo_repo << argocd
    argocd >> app

# Diagram 3: Only ArgoCD (GitOps for Everything)
with Diagram(
    "3. Only ArgoCD (GitOps for Everything)",
    show=False,
    filename="../blog/static/diagrams/eks-all-argocd",
    direction="TB",
    outformat="png",
    graph_attr=graph_attr
):
    argo_repo = Git("GitOps Codebase")
    aws_api = APIGateway("AWS API")

    with Cluster("AWS Account"):
        with Cluster("EKS Cluster"):
            eks = EKS("EKS Control Plane")
            nodegroups = EC2("Node Groups")
            podidentities = IAMRole("Pod Identities")
            with Cluster("Kubernetes"):
                argocd = ArgoCD("ArgoCD")
                app = Pod("App Deployment")
                controller = Pod("Controller")
                argocd >> [app, controller]
                controller >> aws_api

        iam = IAMRole("IAM Roles")
        rds = RDS("RDS")
        elb = ELB("Load Balancer")

    argo_repo << argocd
    aws_api >> [iam, rds, elb, eks, nodegroups, podidentities]
