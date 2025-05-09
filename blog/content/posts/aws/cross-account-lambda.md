---
title: "Using images stored in ECR for AWS Lambda"
date: 2025-05-09
draft: false
ShowToc: true
tags: ["aws", "lambda", "ecr"]
---

## Introduction 

Since the introduction of AWS Lambda, supported runtime kept growing. Around 2020, support for containerized Lambdas was added. In this post, I'm going to walk you through what's required for running Lambdas using the images stored in ECR. I will cover simple scenarios, where the ECR repository is located in the same account, a more complex scenario where the repository is in another account, as well as a scenario for larger organizations, which are adopting a multi-account setup with AWS Organizations.

In this blog post, I will be stricly focusing on the permissions aspect. In my opinion, the official [AWS Documentation](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html) is very approachable and detailed enough about the process of building containers images for Lambdas, but is slightly scarce when it comes to the necessary permissions. Regardless of my opinion, [here's a link](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html#gettingstarted-images-permissions) to the official documentation on the permissions aspect.

## Prerequisites

For the purposes of this blog post, I created two AWS Accounts. I am using AWS Organizations, because it makes it trivial to create additional accounts plus it makes it trivial to clean it up later. I also wanted to cover a multi-account setup with AWS Organizations and we'll get there in a later section of this post.

In one of the accounts, I created three ECR repositories:
- 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account
- 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-another-account
- 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations

Repository policies will be assigned to the ECR Repositories respective to the scenario covering.

I'm also building and pushing exactly the same container image to all of these repositories. I decided to try python:

```python
# lambda_function.py

import sys
def handler(event, context):
    return 'Hello from AWS Lambda using Python' + sys.version + '!'
```

```Dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY lambda_function.py ${LAMBDA_TASK_ROOT}

CMD [ "lambda_function.handler" ]
```

Finally, here's how I build it and push it to respective ECR repositories:
```shell
# build the image
$ docker build . --provenance=false \
-t 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account:0.0.1 \
-t 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-another-account:0.0.1 \
-t 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations:0.0.1

# ... removed for brevity                                                                                                                                                                                                                                                            0.0s
 => => writing image sha256:cbc077db751f54a4b2615fc9a41f274bb1fd2ec47b53c467deaa4d4074bff131                                                                                                                                                                                                                                                          0.0s
 => => naming to 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account:0.0.1                                                                                                                                                                                                                                                            0.0s
 => => naming to 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-another-account:0.0.1                                                                                                                                                                                                                                                         0.0s
 => => naming to 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations:0.0.1                                                                                                                                                                                                                                                       0.0s

# login to ECR
demo $ aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 813835382529.dkr.ecr.eu-central-1.amazonaws.com
# ... removed for brevity
Login Succeeded

# push the images
$ docker push 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account:0.0.1
# ...
0.0.1: digest: sha256:d6e5cc55766f98a72111e769640d54ac83a201ff18cb40a2547055de7def5825 size: 1785

$ docker push 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-another-account:0.0.1 
# ...
0.0.1: digest: sha256:d6e5cc55766f98a72111e769640d54ac83a201ff18cb40a2547055de7def5825 size: 1785

$ docker push 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations:0.0.1
# ...
0.0.1: digest: sha256:d6e5cc55766f98a72111e769640d54ac83a201ff18cb40a2547055de7def5825 size: 1785
```

We can also make sure the image we've just built works by locally testing it:
```shell
$ docker run -d -p 9000:8080 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account:0.0.1
94c8ffc1dc7dfe6e50d01fa8e43f429183c231a70b0c7ba7d83db484b4b24d4e
$ curl "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{}'
"Hello from AWS Lambda using Python3.12.9 (main, Apr  9 2025, 10:25:36) [GCC 11.5.0 20240719 (Red Hat 11.5.0-5)]!"
```

LGTM. :)

In addition to the image, we'll also need an IAM Role for our Lambda. Here's how we can do that:
```shell
$ cat <<EOF > lambda-trust-policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sts:AssumeRole"
            ],
            "Principal": {
                "Service": [
                    "lambda.amazonaws.com"
                ]
            }
        }
    ]
}
EOF

$ aws iam create-role --role-name LambdaRoleWithoutPermissions --assume-role-policy-document file://lambda-trust-policy.json
# ...
        "Arn": "arn:aws:iam::813835382529:role/LambdaRoleWithoutPermissions",
# ...
```

The Lambda role creation step must be repeated in the other account in multi-account scenarios.

## Lambda and ECR repository in the same account

```shell
$ aws lambda create-function \
--function-name test-same-account \
--role "arn:aws:iam::813835382529:role/LambdaRoleWithoutPermissions" \
--package-type Image \
--code ImageUri=813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account:0.0.1
```

In my situation it worked, but I was using a powerful role to create the Lambda, which had the capability of modifying the ECR Repository policy. After inspecting the policies, I found this one to be automatically added to my ECR Repository:
```json
{
  "Statement": [
    {
      "Condition": {
        "StringLike": {
          "aws:sourceArn": "arn:aws:lambda:eu-central-1:813835382529:function:*"
        }
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:DeleteRepositoryPolicy",
        "ecr:GetDownloadUrlForLayer",
        "ecr:GetRepositoryPolicy",
        "ecr:SetRepositoryPolicy"
      ],
      "Principal": {
        "Service": [
          "lambda.amazonaws.com"
        ]
      },
      "Effect": "Allow",
      "Sid": "LambdaECRImageRetrievalPolicy"
    }
  ],
  "Version": "2008-10-17"
}
```

If least-privileged principle was followed properly and the role used to create the Lambda couldn't modify ECR Repository's permissions, Lambda creation would fail. Let's test it. 

First, I've cleared this repository's permissions. I am creating another IAM Role called `LimitedLambdaRole` and assigning predefined `AWSLambda_FullAccess` which doesn't include any ECR permissions. Then, I am switching the role and attempting to create the Lambda function again.

```shell
# switch role ([kudos to Nev from stackoverflow](https://stackoverflow.com/a/67636523))
$ export $(printf "AWS_ACCESS_KEY_ID=%s AWS_SECRET_ACCESS_KEY=%s AWS_SESSION_TOKEN=%s" \
> $(aws sts assume-role \
> --role-arn arn:aws:iam::813835382529:role/LimitedLambdaRole \
> --role-session-name Test \
> --query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]" \
> --output text))

# Confirm whoami
$ aws sts get-caller-identity
{
    "UserId": "AROA327C6N4AUOWAVWF2Y:Test",
    "Account": "813835382529",
    "Arn": "arn:aws:sts::813835382529:assumed-role/LimitedLambdaRole/Test"
}

# Create lambda
$ aws lambda create-function \
> --function-name test-same-account \
> --role "arn:aws:iam::813835382529:role/LambdaRoleWithoutPermissions" \
> --package-type Image \
> --code ImageUri=813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account:0.0.1

An error occurred (AccessDeniedException) when calling the CreateFunction operation: Lambda does not have permission to access the ECR image. Check the ECR permissions.
```

I love the fail-fast strategy implemented here by AWS. Nothing would be more annoying than finding out that the permissions are incorrect only after trying to run your function. ;)

Let's see if it's gonna work again if proper policy is assigned to the ECR repository. I am assigning the following one to the lambda-same-account ECR repo.

```json
{
   "Sid":"LambdaECRImageRetrievalPolicy",
   "Effect":"Allow",
   "Principal":{
      "Service":"lambda.amazonaws.com"
   },
   "Action":[
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
   ]
}
```

... and attempting to create the Lambda again:

```shell
$ aws lambda create-function \
  --function-name test-same-account \
  --role "arn:aws:iam::813835382529:role/LambdaRoleWithoutPermissions" \
  --package-type Image \
  --code ImageUri=813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-same-account:0.0.1
{
    "FunctionName": "test-same-account",
    "FunctionArn": "arn:aws:lambda:eu-central-1:813835382529:function:test-same-account",
    "Role": "arn:aws:iam::813835382529:role/LambdaRoleWithoutPermissions",
# ... removed for brevity

# test the lambda
$ aws lambda invoke --function-name test-same-account /dev/stdout
{Hello from AWS Lambda using Python3.12.9 (main, Apr  9 2025, 10:25:36) [GCC 11.5.0 20240719 (Red Hat 11.5.0-5)]!"
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
```

## Lambda and ECR repository in separate accounts

We'll cover a scenario where ECR repository and Lambda are in two distinct accounts. We'll use `813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-another-account:0.0.1` for a Lambda in `592444418872` account.

Please note that an IAM Role for Lambda must be created. See [Prerequisites](#prerequisites) for more information. It is assumed below that such role is already created.

Let's try by creating a Lambda and inspecting the error message:
```shell
# Confirm we're on the right account
$ aws sts get-caller-identity | grep Account
     "Account": "592444418872",


# 
$ aws lambda create-function \
  --function-name test-another-account \
  --role "arn:aws:iam::592444418872:role/LambdaRoleWithoutPermissions" \
  --package-type Image \
  --code ImageUri=813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-another-account:0.0.1
An error occurred (AccessDeniedException) when calling the CreateFunction operation: Lambda does not have permission to access the ECR image. Check the ECR permissions.
```

As expected, Lambda creation failed. Let's fix it by attaching a correct policy to the ECR Repository in the account hosting it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CrossAccountPermission",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Principal": {
        "AWS": "arn:aws:iam::592444418872:root"
      }
    },
    {
      "Sid": "LambdaECRImageCrossAccountRetrievalPolicy",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Condition": {
        "StringLike": {
          "aws:sourceARN": "arn:aws:lambda:*:592444418872:function:*"
        }
      }
    }
  ]
}
```

... and try creating the Lambda again:

```shell
~ $ aws lambda create-function \
>   --function-name test-another-account \
>   --role "arn:aws:iam::592444418872:role/LambdaRoleWithoutPermissions" \
>   --package-type Image \
>   --code ImageUri=813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-another-account:0.0.1
{
    "FunctionName": "test-another-account",
    "FunctionArn": "arn:aws:lambda:eu-central-1:592444418872:function:test-another-account",
    "Role": "arn:aws:iam::592444418872:role/LambdaRoleWithoutPermissions",
# ... removed for brevity

# Finally test it
$ aws lambda invoke --function-name test-another-account /dev/stdout
{Hello from AWS Lambda using Python3.12.9 (main, Apr  9 2025, 10:25:36) [GCC 11.5.0 20240719 (Red Hat 11.5.0-5)]!"
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
```

## Lambda and ECR Repository in separate accounts, using AWS Organizations

Bigger organizations may end up with multiple accounts. Centralizing the ECR inventory in a single account is a viable strategy for managing the images and other OCI artifacts. Specifying every single account is not a scalable solution in such a scenario, for two reasons: with tens or hundreds accounts, the policy would grow huge. More importantly, adding or removing accounts would involve updating the policies for all of the ECR repositories. Thankfully we can write our permissions in such a way to select all the accounts belonging to our organization (or suborganization).

We're going to reuse the two accounts previously used, but use the third repository: `813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations`. Both of the accounts belong to the same organization, but it could work across organizations too.

Let's try creating the Lambda to confirm policies are not set:

```shell
$ aws lambda create-function \
  --function-name test-organizations \
  --role "arn:aws:iam::592444418872:role/LambdaRoleWithoutPermissions" \
  --package-type Image \
  --code ImageUri=813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations:0.0.1

An error occurred (AccessDeniedException) when calling the CreateFunction operation: Lambda does not have permission to access the ECR image. Check the ECR permissions.
```

There's two conditions you can use to target accounts belonging to an organization - `aws:SourceOrgID` and `aws:SourceOrgPaths`. Which one should you use? SourceOrgID is great if you want to target all of the accounts under your organization. SourceOrgPaths is useful when you have a multi-level hierarchy and want to share with a subset of the hierarchy. A common scenario is setting up separate group for production and development accounts, so you can easily target all-production all all-non-production accounts.

Here's a sample policy using a combination of `aws:PrincipalOrgId` and `aws:SourceOrgID` conditions.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Condition": {
        "StringEquals": {
          "aws:PrincipalOrgId": "<YOUR_ORG_ID>"
        }
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Principal": {
        "AWS": [
          "*"
        ]
      },
      "Effect": "Allow",
      "Sid": "CrossAccountPermission"
    },
    {
      "Condition": {
        "StringEquals": {
          "aws:SourceOrgId": "<YOUR_ORG_ID>"
        }
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Principal": {
        "Service": [
          "lambda.amazonaws.com"
        ]
      },
      "Effect": "Allow",
      "Sid": "LambdaECRImageCrossAccountRetrievalPolicy"
    }
  ]
}
```

First, let's verify that the allmighty user can pull the image:
```shell
$ aws ecr get-login-password --region eu-central-1 | docker login --username AWS --password-stdin 813835382529.dkr.ecr.eu-central-1.amazonaws.com
# ...
Login Succeeded

$ docker pull 813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations:0.0.1
0.0.1: Pulling from lambda-aws-organizations
# ....
813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations:0.0.1
```

Now, let's try creating a Lambda:
```shell
$ aws lambda create-function \
  --function-name test-organizations \
  --role "arn:aws:iam::592444418872:role/LambdaRoleWithoutPermissions" \
  --package-type Image \
  --code ImageUri=813835382529.dkr.ecr.eu-central-1.amazonaws.com/lambda-aws-organizations:0.0.1
# ...

# test
$ aws lambda invoke --function-name test-organizations /dev/stdout
{Hello from AWS Lambda using Python3.12.9 (main, Apr  9 2025, 10:25:36) [GCC 11.5.0 20240719 (Red Hat 11.5.0-5)]!"
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
```

Another way of representing the policy would be using `PrincipalOrgPaths` and `SourceOrgPaths`. Replace `<YOUR_ORG_PATH_PREFIX>` accordingly (example: `o-abcdef/*`). You may provide more than one organization path here.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Condition": {
        "ForAnyValue:StringLike": {
          "aws:PrincipalOrgPaths": ["<YOUR_ORG_PATH_PREFIX>"]
        }
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Principal": {
        "AWS": [
          "*"
        ]
      },
      "Effect": "Allow",
      "Sid": "CrossAccountPermission"
    },
    {
      "Condition": {
        "ForAnyValue:StringLike": {
          "aws:SourceOrgPaths": ["<YOUR_ORG_PATH_PREFIX>"]
        }
      },
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Principal": {
        "Service": [
          "lambda.amazonaws.com"
        ]
      },
      "Effect": "Allow",
      "Sid": "LambdaECRImageCrossAccountRetrievalPolicy"
    }
  ]
}
```