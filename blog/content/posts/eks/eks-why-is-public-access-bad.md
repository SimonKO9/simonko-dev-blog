---
title: "Why You Shouldn't Keep Your EKS API Access Open to the Internet"
date: 2025-05-05
draft: false
ShowToc: true
tags: ["eks", "kubernetes", "security"]
---

## Introduction

The control plane is a set of components that together form the management layer of Kubernetes. These components manage the cluster's state, coordinate between nodes, and provide APIs for interacting with the cluster. The security of this API component, known as the API Server, is the focus of today's post. Ensuring the security of the API Server is critical because it serves as the interface to your cluster. It is used by both users and automation tools to interact with the cluster. Whether it's `kubectl`, Helm, ArgoCD, or any other tool, they all communicate with the cluster via the API. Unauthorized access can lead to a complete or partial cluster compromise, data breaches, or service disruptions.

In managed solutions like EKS, AKS, or GKE, the infrastructure hosting the control plane is managed by the cloud provider. However, securing access to the API endpoint falls under the shared responsibility model, meaning you are responsible for configuring access controls and managing network exposure.

## EKS

"AWS EKS provides configurable endpoint access modes for the cluster API:
- **Public cluster endpoint**, which is accessible from the Internet.
- **Private cluster endpoint**, which ensures that traffic stays within the VPC.

Both options come with their own advantages and disadvantages, as well as different ways of securing access. Enabling only the private endpoint means the API server is only reachable from within your VPC.

For a detailed description of both access endpoints, refer to [the official documentation](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access).

## Securing Access to the Cluster API

There are several ways of improving the security of accessing the Kubernetes API. By combining them, you can implement robust multi-layered protection.

Two main reasons for implementing such a complex, tiered approach are:
- **Misconfigurations**: Accidental misconfigurations happen. Limiting network exposure reduces the potential impact if RBAC or other controls are incorrectly set up.
- **Zero-day vulnerabilities**: While less common, vulnerabilities in the Kubernetes API server or authentication mechanisms could be exploited if the endpoint is publicly accessible.

### Network Security

Access to a Kubernetes cluster is primarily controlled by RBAC. In EKS, IAM principals (users or roles) are mapped to Kubernetes RBAC entities, allowing AWS credentials to authorize actions within the cluster via the API server. With public access enabled, leaked AWS credentials pose a significant risk — an attacker could potentially gain access to your cluster from anywhere on the internet without needing prior network access.

One way to mitigate this risk is by restricting access to the Kubernetes API to specific CIDRs, such as your corporate network. However, corporate networks should not be considered secure (insecure WiFi, phishing attacks or insider threats). Companies often implement multiple layers of authentication to protect services, even those not exposed to the public.

*My recommendation is to disable the public endpoint and enable the private endpoint.*
This recommendation aligns with the [Security Checklist](https://kubernetes.io/docs/concepts/security/security-checklist/#network-security) in the Kubernetes documentation. Limit access to the cluster API to specific security groups or a highly secure and tightly monitored bastion host.

Some may argue that maintaining a bastion or jump host is cumbersome or merely shifts the responsibility. While managing access is still required, consider these points:
- Such an instance does not need a public IP; you can use AWS Systems Manager Session Manager to connect securely via AWS APIs without opening inbound ports.
- You might not need dedicated EC2 instances at all. AWS CloudShell can be configured to run within your VPC, providing CLI access from the AWS console without needing a dedicated bastion.

### Use the Minimum Set of Permissions

*Apply the principle of least privilege—grant users only the minimum permissions they need*:
- Avoid granting `exec` access to pods with powerful service accounts (just don't do it).
- Consider restricting users from reading secrets.
- If necessary, allow for *temporary* permission elevation to carry out troubleshooting activities.

Refer to the official [Security Checklist](https://kubernetes.io/docs/concepts/security/security-checklist/#pod-security) in the Kubernetes documentation for more details.

Access to application logs and metrics outside the cluster significantly reduces the need for direct cluster access.

These principles apply to both RBAC and IAM. For IAM specifically:
- Use two-factor authentication.
- Use short-lived access credentials for AWS API access.

### Use GitOps

Adopt a pull-based model with GitOps. This approach enhances security by reducing the need for users or CI/CD systems to have direct administrative credentials to the cluster for application deployment. Instead, the GitOps agent running within the cluster pulls changes from a repository. While the GitOps agent itself requires cluster credentials (typically a Service Account), these are specific to the agent and can be tightly scoped and not used outside of the cluster. 

Git credentials may leak too, but these can be mitigated by following these practices:
- Protecting the `main` branch (or any branch the GitOps tool monitors) from pushing directly to it.
- Requiring pull requests with mandatory approvals for changes.

Additionally, adopting GitOps can help prevent cluster misconfigurations caused by manual changes that were supposed to be temporary. :) With required approvals, you get another set of eyes, and undoing the changes is a matter of `git revert`.

### Patch Regularly

Keep your cluster and its components up to date. While AWS handles security patches for the EKS control plane, you are responsible for Kubernetes version upgrades. Additionally:
- Update your Node Groups to the latest AMIs (using managed Node Groups and node lifecycle tools like Karpenter can greatly simplify this).
- Regularly patch EKS add-ons.
- Update the container images of your running workloads.

## Conclusion

Using multiple layers of defense is essential for effectively securing access to your cluster.
