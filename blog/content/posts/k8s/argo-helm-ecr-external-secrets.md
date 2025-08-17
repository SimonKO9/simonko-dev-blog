---
title: "How to deploy Helm charts stored in private ECR with Argo CD?"
date: 2025-07-21
draft: false
ShowToc: true
tags: ["gitops", "kubernetes", "argocd", "helm", "ecr"]
description: "A practical guide to deploying Helm charts from a private ECR repository with ArgoCD with help of External Secrets."
---

## Introduction

In my [previous blog post](/posts/k8s/deploying-helm-charts-from-oci-with-argo/) I went over deploying Helm Charts from OCI registries. Today, I'd like to talk about ECR specifically and share with you an approach for managing access to ECR for ArgoCD in a secure and fully automated manner.

## Problem description

For ArgoCD to access Helm charts from private OCI registry, a set of credentials must be defined as a Kubernetes Secret object, similarly to the following:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: private-ecr-repo
  namespace: argocd
  labels:
    argocd.argoproj.io/secret-type: repository
stringData:
  url: 1234567890.dkr.ecr.eu-central-1.amazonaws.com
  name: private-ecr
  type: helm
  enableOCI: "true"
  username: AWS
  password: <placeholder-for-aws-ecr-token>
```

AWS credentials can be exchanged for an ECR token, for example by running `aws ecr get-login-password`. The problematic part is that such a token is only valid for 12 hours. The solution would be a mechanism which issues a token and updates the Secret every now and then, before the token expires.

There's [a GitHub repo accompanying this blog post](https://github.com/SimonKO9/blog-demos-k8s/tree/main/002-argo-helm-ecr-eso), where you can find reference code snippets and additional docs.

## The solution

The most elegant solution I found to this problem is by leveraging [External Secrets Operator's generators](https://external-secrets.io/latest/guides/generator/), [ECR Generator specifically](https://external-secrets.io/latest/api/generator/ecr/).

### A brief explanation what External Secrets Operator is what generators do

External Secrets Operator, often shortened to ESO, is a Kubernetes operator that integrates external secrets stores with Kubernetes. For example, it can read secret data from HashiCorp Vault or AWS Secrets Manager and populate Kubernetes secrets with that information.

Generators is a powerful feature of ESO which lets you, as the name suggests, generate values. It can be used to generate random passwords, UUIDs, or... retrieve an ECR authorization token.

You can read more about the ECR generator and find information about other generators in the  [official documentation](https://external-secrets.io/latest/api/generator/ecr/).

## Step by step guide

In this section, I'll take you over the steps required to implement what we just talked about. 

Here's what we're going to do:
1. Create a private ECR repository and store a Helm chart there, 
2. Spin up a local k8s cluster with ArgoCD and External Secrets Operator,
3. Define an ExternalSecret using ECRAuthorizationToken generator,
4. And finally deploy a Helm chart created in the first step.

### Create ECR

I created a private ECR repository called `helm/nginx-ingress`. I will store the official nginx-ingress Helm chart there (for demo purposes).

```sh
# Add nginx repository
$ helm repo add nginx-stable https://helm.nginx.com/stable
$ helm repo update

# Pull the latest version
$ helm pull nginx-stable/nginx-ingress
# it downloaded version 2.2.2
$ ls nginx*
nginx-ingress-2.2.2.tgz
```

I then signed in to my ECR using Helm CLI and and uploaded the chart. 

Note: I am using a temporary account that I created solely for this blog post (AWS Organizations makes it trivial). I'll terminate it once the blog post is ready for publishing. :)

```sh
# Sign in
$ aws ecr get-login-password --region eu-central-1 | helm registry login \
  --username AWS \
  --password-stdin \
  886036506409.dkr.ecr.eu-central-1.amazonaws.com

# Push to ECR
$ helm push nginx-ingress-2.2.2.tgz oci://886036506409.dkr.ecr.eu-central-1.amazonaws.com/helm             
Pushed: 886036506409.dkr.ecr.eu-central-1.amazonaws.com/helm/nginx-ingress:2.2.2
Digest: sha256:afd1fa779c215fd96f0d12b3f202528901c74c86f7074b6a63e6610add4f7940
```

Please note that I skipped the name of the chart - helm adds it automatically:
```sh
helm push nginx-ingress-2.2.2.tgz oci://886036506409.dkr.ecr.eu-central-1.amazonaws.com/helm/nginx-ingress
Error: failed to perform "Push" on destination: POST "https://886036506409.dkr.ecr.eu-central-1.amazonaws.com/v2/helm/nginx-ingress/nginx-ingress/blobs/uploads/": response status code 404: name unknown: The repository with name 'helm/nginx-ingress/nginx-ingress' does not exist in the registry with id '886036506409'
```

### Start and setup Kubernetes

I am using KinD and Podman. I invite you to have a look at https://github.com/SimonKO9/blog-demos-k8s/tree/main/000-local-k8s if you're looking for guidance on starting up a local KinD cluster with Podman.

```sh
$ kind cluster create
# once the cluster is created, kubectl is automatically configured

# Verify nodes and kubectl
$ kubectl get nodes
NAME                 STATUS   ROLES           AGE     VERSION
kind-control-plane   Ready    control-plane   2m20s   v1.33.1

# Verify everything's up
$ kubectl get po -A
NAMESPACE            NAME                                         READY   STATUS    RESTARTS   AGE
kube-system          coredns-674b8bbfcf-4cj52                     1/1     Running   0          2m16s
kube-system          coredns-674b8bbfcf-9n2hn                     1/1     Running   0          2m16s
kube-system          etcd-kind-control-plane                      1/1     Running   0          2m24s
kube-system          kindnet-qqnzb                                1/1     Running   0          2m16s
kube-system          kube-apiserver-kind-control-plane            1/1     Running   0          2m23s
kube-system          kube-controller-manager-kind-control-plane   1/1     Running   0          2m23s
kube-system          kube-proxy-lvr5q                             1/1     Running   0          2m16s
kube-system          kube-scheduler-kind-control-plane            1/1     Running   0          2m24s
local-path-storage   local-path-provisioner-7dc846544d-lfnr5      1/1     Running   0          2m16s
```

Next, I deploy ArgoCD and External Secrets.

```sh
ARGOCD_VERSION="v3.0.11"
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml


helm repo add external-secrets https://charts.external-secrets.io

helm install external-secrets \
   external-secrets/external-secrets \
  -n external-secrets \
  --create-namespace
```

### Configure ESO to create (and refresh) ArgoCD repo-secret

```yaml
apiVersion: generators.external-secrets.io/v1alpha1
kind: ECRAuthorizationToken
metadata:
  name: ecr-gen-helm
  namespace: argocd
spec:
  region: eu-central-1
  auth:
    secretRef:
      accessKeyIDSecretRef:
        name: "ecr-access"
        key: "access_key"
      secretAccessKeySecretRef:
        name: "ecr-access"
        key: "secret_access_key"
---
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: ecr-helm
  namespace: argocd
spec:
  refreshInterval: "1h"
  target:
    name: ecr-reposecret
    creationPolicy: Owner
    deletionPolicy: Retain
    template:
      type: Opaque
      data:
        url: 886036506409.dkr.ecr.eu-central-1.amazonaws.com
        type: "helm"
        name: "ecr-helm"
        enableOCI: "true"
        username: "{{ .username }}"
        password: "{{ .password }}"
      metadata:
        labels:
          argocd.argoproj.io/secret-type: repository
  dataFrom:
    - sourceRef:
        generatorRef:
          apiVersion: generators.external-secrets.io/v1alpha1
          kind: ECRAuthorizationToken
          name: "ecr-gen-helm"
```

There's a few things happening here worth explanation. First, I create an ECRAuthorizationToken, which is the definition of the generator. We have to tell ESO how to authenticate with AWS - in this scenario, I am simply telling it to use static credentials which I stored in another Kubernetes Secret. In case of EKS, it's better (and recommended) to use IRSA or Pod Identity instead.

Here's how I did it:
```sh
$ kubectl create secret generic ecr-access --from-literal=access_key=CHANGEME --from-literal=secret_access_key=CHANGEME -n argocd
```

Second, I create an ExternalSecret, which uses a template and references the generator. The template is used by ESO when creating an actual Secret. It has to meet the requirements of an ArgoCD repo secret. The secret will be refreshed every hour.

After a very brief moment, you should be able to see the secret created and the ExternalSecret status would say synced:

```sh
kubectl get externalsecret -n argocd
NAME       STORETYPE   STORE   REFRESH INTERVAL   STATUS         READY
ecr-helm                       1h                 SecretSynced   True

$ kubectl get secret -n argocd        
NAME                          TYPE     DATA   AGE
argocd-initial-admin-secret   Opaque   1      7h22m
argocd-notifications-secret   Opaque   0      7h22m
argocd-redis                  Opaque   1      7h22m
argocd-secret                 Opaque   5      7h22m
ecr-access                    Opaque   2      18m
ecr-reposecret                Opaque   6      14m
```

You can also inspect if the reposecret is fine, e.g. using argocd CLI:
```sh
argocd repo list
TYPE  NAME      REPO                                             INSECURE  OCI   LFS    CREDS  STATUS      MESSAGE  PROJECT
helm  ecr-helm  886036506409.dkr.ecr.eu-central-1.amazonaws.com  false     true  false  true   Successful           
```

Make sure the region is set correctly for the ECRAuthorizationToken object, as well as the account ID and region are correct in the ECR URL.

### Deploy an app to test

Finally, I apply the following Application manifest to the cluster to check if ArgoCD will truly deploy a Helm Chart from my ECR:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: nginx-ingress
  namespace: argocd
  finalizers:
  - resources-finalizer.argocd.argoproj.io  
spec:
  project: default
  source:
    helm: {}
    chart: helm/nginx-ingress
    repoURL: 886036506409.dkr.ecr.eu-central-1.amazonaws.com
    targetRevision: 2.2.2
  destination:
    server: https://kubernetes.default.svc
    namespace: nginx-ingress
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

## Further improvements

I consider this setup quite solid, except for the fact that we're storing long-lived AWS credentials for ESO. A proper solution would use Pod Identities (or IRSA).

## Summary

In this blog post we've seen how ESO can help us automate ECR credential refresh for ArgoCD. I believe this is the most elegant way and uses standardized tools over custom solutions. It would be perfect if ArgoCD integrated with ECR natively, but at the time of writing this blog post - it doesn't. Let me know in the comments what you think and if you have other suggestions!