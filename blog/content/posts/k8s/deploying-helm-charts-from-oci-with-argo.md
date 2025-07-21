---
title: "Deploying Helm Charts from an OCI registry with ArgoCD"
date: 2025-07-21
draft: false
ShowToc: true
tags: ["gitops", "kubernetes", "argocd", "helm"]
description: "A practical guide to deploying Helm charts from OCI registries using ArgoCD, covering both direct and umbrella chart approaches."
---

## Introduction

In this blog post, I'll demonstrate two methods for deploying Helm charts stored in an OCI registry using ArgoCD. For this demonstration, I'm using a Kind cluster, but the process is the same regardless of your Kubernetes environment.

Before OCI support, Helm charts were typically stored in custom chart repositories (ChartMuseum, Nexus, Artifactory) or in Git repositories.

OCI registries have become a popular way to store and distribute Helm charts, providing a standardized approach similar to container images. Helm added experimental support for OCI registries in v3, and it [became generally available in Helm 3.8.0](https://github.com/helm/helm/releases/tag/v3.8.0). It's a very convenient solution for organizations already leveraging container registries, as they already have what's needed for storing their charts.

You can read more about OCI support in Helm [here](https://helm.sh/docs/topics/registries/).

### Prerequisites

Please ensure the following prerequisites are met:

1. A running Kubernetes cluster.
2. `kubectl` installed and configured to communicate with your cluster.
3. ArgoCD deployed (I am using v3.0.11).
4. A Git repository available for ArgoCD to reference.

This post is accompanied by a [GitHub repository](https://github.com/SimonKO9/blog-demos-k8s/tree/argo-helm/001-argo-helm) containing all examples  for Helm chart deployment. The README also includes instructions for setting up ArgoCD locally.

For a quick guide to setting up a local Kubernetes cluster using kind and podman, see [this repository](https://github.com/SimonKO9/blog-demos-k8s/tree/argo-helm/000-local-k8s).

## Helm Chart Deployment

There are two main ways to deploy a Helm chart using an ArgoCD Application: referencing a Helm chart directly in an Application object, or using an umbrella chart.

In the examples below, I'll show you how to deploy Bitnami nginx chart stored in the Docker Hub OCI Registry and share what's needed for deploying from a private registry.

### Using a Helm Chart Directly

Apply the following YAML to your cluster:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: argo-helm-direct
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io  
spec:
  project: default
  source:
    helm:
      valuesObject:
        service:
          type: ClusterIP
    chart: nginx
    repoURL: registry-1.docker.io/bitnamicharts
    targetRevision: 21.0.8
  destination:
    server: https://kubernetes.default.svc
    namespace: direct
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

At first, it may seem confusing that specifying the `oci://` protocol is not required here. How does ArgoCD know to source this chart from an OCI registry? It turns out that ArgoCD uses an auto-detection mechanism: if the protocol is missing (typically http/https), it assumes the repository is OCI-based. See [this code reference](https://github.com/argoproj/argo-cd/blob/v3.0.11/util/helm/client.go#L399) and [types.go](https://github.com/argoproj/argo-cd/blob/v3.0.11/pkg/apis/application/v1alpha1/types.go#L316) for details.

### Private Repositories

To use ArgoCD with a private OCI registry, you must create a repository secret. Note that `enableOCI` must be set to `"true"` to access OCI-based registries, even if the registry is public. Valid credentials are also required.

For example, referencing a Helm chart stored in AWS ECR will require a repository secret similar to the following:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bitnami-oci-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  url: <AWS-ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com
  name: private-oci
  type: helm
  enableOCI: "true"
  username: AWS
  password: <placeholder-for-aws-ecr-token>
```

I am using AWS ECR and a temporary token can be generated using the following command:
```sh
aws ecr get-login-password --region <region>
```

> **Note:** ECR tokens are only valid for 12 hours. You need a way to refresh these, or ArgoCD will fail to download charts when the token expires. I recommend using ExternalSecrets, which supports credential refresh at intervals. See [this GitHub comment](https://github.com/argoproj/argo-cd/issues/20810#issuecomment-2518745195) for inspiration.

### Using an Umbrella Chart

For this approach, you'll need a Git repository. You can use [an example I prepared for you](https://github.com/SimonKO9/blog-demos-k8s/tree/main/001-argo-helm/umbrella-chart), which is public and doesn't require repository secret.

Create an application and apply it to your cluster:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: argo-helm-umbrella
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io  
spec:
  project: default
  source:
    path: 001-argo-helm/umbrella-chart
    repoURL: https://github.com/SimonKO9/blog-demos-k8s.git
    targetRevision: main
  destination:
    server: https://kubernetes.default.svc
    namespace: umbrella
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

The key file is the umbrella chart definition, `Chart.yaml`, which lists your dependencies:

```yaml
# Chart.yaml
apiVersion: v2
name: umbrella-chart
description: Umbrella chart to deploy Bitnami nginx
type: application
version: 0.1.0
dependencies:
  - name: nginx
    version: 21.0.6
    repository: oci://registry-1.docker.io/bitnamicharts
appVersion: "1.0"
```

Values for the `nginx` chart can be supplied using the `values.yaml` file. All nginx-specific properties must be prefixed with `nginx.`. For example, to set `service.type`, use `nginx.service.type`. The `name` field is used as a prefix unless an alias is specified. Read [more about aliases here](https://helm.sh/docs/topics/charts/#alias-field-in-dependencies).

Example `values.yaml`:

```yaml
# values.yaml
nginx:
  service:
    type: ClusterIP
```

---

## Summary

This post covered two methods for deploying Helm charts from OCI registries using ArgoCD: direct chart referencing and the umbrella chart pattern. Both approaches support public and private registries.

Each method has its strengths. Umbrella charts are useful when you need to extend the original chart or combine multiple services under a single release. Separate Application resources are ideal for true microservice architectures, where services are independent and charts are self-contained, allowing customization through values as needed.