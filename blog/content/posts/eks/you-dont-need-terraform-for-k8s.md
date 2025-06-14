---
title: "You don't need Terraform for your Managed Kubernetes anymore"
date: 2025-06-08
draft: false
ShowToc: true
tags: ["eks", "kubernetes", "security", "managed kubernetes", "aks", "gke"]
---

## Introduction and motivation

Have you ever questioned using Terraform (or any other external IaC tool) for your Kubernetes configuration?
Have you resorted to using Terraform just because you couldn't manage your Managed Node Groups or Pod Identities?
Wouldn't it feel more natural if these were simply represented as another resource type in your cluster?

If you answered yes to any of the above, this article is for you. I have. And then I started doing my own research.

My motivation is that I want to manage my clusters and applications in the same way - enable GitOps for infrastructure and leverage ArgoCD (or Flux). I am not suggesting that you should completely abandon Terraform and manage your whole IAM and network configuration with ArgoCD. There's a lot of elegance in configuring the workloads and their requirements the same way. If you wanted to run a database inside Kubernetes, you'd just use a helm chart for that and add it to your GitOps repo. But if you wanted to switch to a managed solution, like RDS, suddenly you'd have to extract that bit to a separate Terraform codebase and configure it elsewhere.

Switching to a model, where both the application and it's infrastructure are defined next to eachother can drastically improve the efficiency at your organisation, enabling self-service for application teams, effectively offering Kubernetes as an all-in-one platform.

## Who is it for?

Definitely not for everyone. It's something to consider for Kubernetes-centric teams or Platform Engineering teams offering Kubernetes-as-a-Service willing to push that to the next level, enabling "Anything you can think of"-as-a-Service in a self-service way.

## Research

### Node Groups 
When I started, I had already known about one tool capable of managing my Node Groups from within the cluster - Karpenter. It's capabilities go well beyond that, but in general this is a tool letting you define your Node Pools as Kubernetes resources:

```yaml
# example, source: https://github.com/aws/karpenter-provider-aws/blob/main/examples/v1/general-purpose.yaml

apiVersion: karpenter.sh/v1
kind: NodePool
metadata:
  name: general-purpose
  annotations:
    kubernetes.io/description: "General purpose NodePool for generic workloads"
spec:
  template:
    spec:
      requirements:
        - key: kubernetes.io/arch
          operator: In
          values: ["amd64"]
        - key: kubernetes.io/os
          operator: In
          values: ["linux"]
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
        - key: karpenter.k8s.aws/instance-category
          operator: In
          values: ["c", "m", "r"]
        - key: karpenter.k8s.aws/instance-generation
          operator: Gt
          values: ["2"]
      nodeClassRef:
        group: karpenter.k8s.aws
        kind: EC2NodeClass
        name: default
```

see: https://karpenter.sh/docs/concepts/nodepools/

### IRSA / Pod Identities (EKS-specific)

Another piece of your EKS cluster requiring configuration is the Pod Identities. 

A very short introduction to the concept of connecting Pods to IAM Roles. Applications deployed to EKS may require access to AWS services, like S3 and DynamoDB. Accessing these requires authenticating with a set of credentials associated with a role with the right set of permissions. Instead of supplying these credentials from "the outside", one can let EKS handle that for us by associating the Service Account with a specific IAM Role (see [this](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)). It's done in a very similar way to EC2 Instance Profiles, if that is what you're familiar with.

EKS administrators have two ways to configure the mapping between AWS IAM and Kubernetes Service Accounts: the old IRSA (IAM Roles For Service Accounts) and the new - Pod Identities. IRSA requires you to define and attach a trust policy to the IAM Role, coupling it with cluster-specific configuration (because you have to provide a namespaced path to your service account).

Pod Identities is the "new way" (introduced in 2023) of achieving the same, just differently. A trust policy is still required, but it's more generic and is not cluttering the role with cluster-specific configuration. The actual binding between IAM and Kubernetes Service Accounts is configured by creating a Pod Identity Association.

This is definitely a much more elegant design, because the cluster configuration is not leaking into IAM anymore and the actual mapping is configured in EKS. Unfortunately, by "EKS" I mean another AWS API here, not something living inside the cluster.

It's not ideal though, as you need something talking to the AWS API and configuring the associations. In the setups I worked with, that was typically done with Terraform, but here we're looking at the alternatives. To me, that alternative would be expressing the Pod Identity Association by a CRD or be part of some configuration object provided by EKS.

On my journey, I stumbled upon [this open GitHub ticket](https://github.com/aws/containers-roadmap/issues/2291). [joshuabaird suggested a solution](https://github.com/aws/containers-roadmap/issues/2291#issuecomment-1955255563) that would meet my expectations. [And so did danielloader](https://github.com/aws/containers-roadmap/issues/2291#issuecomment-2104771614). These brilliant individuals mentioned two tools that have been on my radar for a while now - [AWS Controllers for Kubernetes (ACK)](https://aws-controllers-k8s.github.io/community/docs/community/overview/) and [Crossplane](https://www.crossplane.io).


There's a GKE-specific offering managed by Google - [Config Connector](https://cloud.google.com/config-connector/docs/overview) and [Azure Service Operator](https://github.com/Azure/azure-service-operator) for AKS.

