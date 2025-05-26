---
title: "How to Run AWS Lambda Container Images as a Non-Root User and Satisfy Security Scanners"
date: 2025-05-25
draft: false
ShowToc: true
tags: ["aws", "lambda", "security", "containers"]
---

## Introduction

One of the supported runtimes for AWS Lambda is containers. AWS offers a set of base images with a [Lambda Interface Client](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html#images-ric) built-in, which is required to run your code in the context of AWS Lambda. The actual usage varies depending on your language of choice. The Runtime Interface Client (RIC) is available as a library that you either call directly in your application's entrypoint (in case of Go), or you use the provided entrypoint and pass a name to your handler, which is the case for Python or NodeJS.

There are multiple options for building container images for AWS Lambda and I will refer my readers to the [official documentation on that topic](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html).

## Experiment

Security best practices dictate that containers are run as a non-root user and AWS Lambda is no exception. In fact, AWS takes care of that for us — regardless of the user specified in the image, AWS will always run your Lambda as a custom, non-root user.

```python
# lambda_function.py
import os
import grp

def handler(event, context):
    groups = [g.gr_name for g in grp.getgrall()]
    uid = os.getuid()
    return f"I am {uid} and my groups are {groups}"
```

```Dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY lambda_function.py ${LAMBDA_TASK_ROOT}

CMD [ "lambda_function.handler" ]
```

See the [prerequisites section](https://simonko.dev/posts/aws/cross-account-lambda/#prerequisites) on my other blog post where I create an IAM Role for AWS Lambda without any permissions. Examples below assume that `LambdaRoleWithoutPermissions` role is already created.

```sh
# Create the function
$ aws lambda create-function \
--function-name test-root \
--role "arn:aws:iam::992050069956:role/LambdaRoleWithoutPermissions" \
--package-type Image \
--code ImageUri=992050069956.dkr.ecr.eu-north-1.amazonaws.com/lambda-test:root

{
    "FunctionName": "test-root",
    "FunctionArn": "arn:aws:lambda:eu-north-1:992050069956:function:test-root",
    "Role": "arn:aws:iam::992050069956:role/LambdaRoleWithoutPermissions",
# ...

# Invoke it
$ aws lambda invoke --function-name test-root out && cat out
{
    "StatusCode": 200,
    "ExecutedVersion": "$LATEST"
}
"I am 993 and my groups are ['root', 'bin', 'daemon', 'sys', 'adm', 'tty', 'disk', 'lp', 'mem', 'kmem', 'wheel', 'cdrom', 'mail', 'man', 'dialout', 'floppy', 'games', 'tape', 'video', 'ftp', 'lock', 'audio', 'users', 'nobody']"
```

AWS Lambda seems to always run as user 993, but I couldn't find this documented anywhere in AWS docs, so my recommendation is to not rely on that uid.

We can easily prove that AWS overrides the default user:
```sh
$ docker run -it --rm --entrypoint=/bin/sh 992050069956.dkr.ecr.eu-north-1.amazonaws.com/lambda-test:root
sh-5.2# id
uid=0(root) gid=0(root) groups=0(root)
```

## So what's next?

From a security standpoint, we're set and we've confirmed that our Lambda doesn't run as root. Yet, popular security scanners complain when the default user is set to root. Your organization may require the image to pass that check, despite being OK in runtime, to avoid getting flagged.

So as not to speak without proof, let's check the output from two popular scanners - Trivy and Checkov.

### Trivy

```sh
~ $ trivy fs -q -f table --scanners misconfig .

Report Summary

┌────────────┬────────────┬───────────────────┐
│   Target   │    Type    │ Misconfigurations │
├────────────┼────────────┼───────────────────┤
│ Dockerfile │ dockerfile │         2         │
└────────────┴────────────┴───────────────────┘
Legend:
- '-': Not scanned
- '0': Clean (no security findings detected)


Dockerfile (dockerfile)

Tests: 28 (SUCCESSES: 26, FAILURES: 2)
Failures: 2 (UNKNOWN: 0, LOW: 1, MEDIUM: 0, HIGH: 1, CRITICAL: 0)

AVD-DS-0002 (HIGH): Specify at least 1 USER command in Dockerfile with non-root user as argument
═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════
Running containers with 'root' user can lead to a container escape situation. It is a best practice to run containers as non-root users, which can be done by adding a 'USER' statement to the Dockerfile.

See https://avd.aquasec.com/misconfig/ds002
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# ...
```

### Checkov

```sh
~ $ checkov -f Dockerfile 
[ dockerfile framework ]: 100%|████████████████████|[1/1], Current File Scanned=Dockerfile
[ secrets framework ]: 100%|████████████████████|[1/1], Current File Scanned=Dockerfile

       _               _
   ___| |__   ___  ___| | _______   __
  / __| '_ \ / _ \/ __| |/ / _ \ \ / /
 | (__| | | |  __/ (__|   < (_) \ V /
  \___|_| |_|\___|\___|_|\_\___/ \_/

By Prisma Cloud | version: 3.2.432 

dockerfile scan results:

Passed checks: 2, Failed checks: 2, Skipped checks: 0

# ...

Check: CKV_DOCKER_3: "Ensure that a user for the container has been created"
        FAILED for resource: Dockerfile.
        File: Dockerfile:1-5
        Guide: https://docs.prismacloud.io/en/enterprise-edition/policy-reference/docker-policies/docker-policy-index/ensure-that-a-user-for-the-container-has-been-created

                1 | FROM public.ecr.aws/lambda/python:3.12
                2 | 
                3 | COPY lambda_function.py ${LAMBDA_TASK_ROOT}
                4 | 
                5 | CMD [ "lambda_function.handler" ]
```


## Make the scanner happy

The solution is rather easy: you may switch to a non-root user at the bottom of your Dockerfile without consequences. Lambda will run your image as a non-root user anyway, regardless of the `USER` directive.

```Dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY lambda_function.py ${LAMBDA_TASK_ROOT}

USER 1001:1001 # or any other non-root user

CMD [ "lambda_function.handler" ]
```

**Note:** Setting the `USER` in the Dockerfile is only to satisfy scanners like Trivy and Checkov. AWS Lambda will still run your function as its own non-root user at runtime, regardless of this setting.

This little change makes both Trivy and Checkov happy without impacting your application. In my opinion, this is a much easier and quicker solution than fighting for an exception at your organization.

## Important notes

For your application to work, application sources must be readable by (in case of e.g. Python) or the binary must be executable by the user used to run Lambda.

This is the case by default, because sources added to `$LAMBDA_TASK_ROOT` (`/var/task`) have the following characteristics (by default):
- are owned by `root:root`
- preserve file permissions

When I created `lambda_function.py`, it was created with default permissions:
```sh
sh-5.2# ls -la /var/task
total 12
drwxr-xr-x.  2 root root 4096 May 26 11:27 .
drwxr-xr-x. 24 root root 4096 Apr 17 06:47 ..
-rw-r--r--.  1 root root  175 May 26 11:27 lambda_function.py
```

according to my user mask:
```sh
$ umask
0022
```

If you're curious how it works: the mask is subtracted from the default permissions. In Linux, the default permission set for files is 666 (`rw-rw-rw`), as adding execute by default is considered insecure, and 777 (`rwxrwxrwx`) for directories.

## A final proof

The image can in fact be run as any user:
```sh
$ docker run -it --rm --user=12345:12345 --entrypoint=/bin/sh 992050069956.dkr.ecr.eu-north-1.amazonaws.com/lambda-test:root
sh-5.2$ id
uid=12345 gid=12345 groups=12345

sh-5.2$ cat /var/task/lambda_function.py 
import os
import grp

def handler(event, context):
    groups = [g.gr_name for g in grp.getgrall()]
    uid = os.getuid()

    return f"I am {uid} and my groups are {groups}"
```    

## TL;DR; - Key Takeaways

- AWS Lambda always runs containers as a non-root user.
- Security scanners may still require a `USER` directive in your Dockerfile.
- Adding a `USER` directive to your `Dockerfile` satisfies scanners without affecting Lambda runtime behavior.
- Make sure your application files are readable/executable by non-root users.

## References

- [Create a Lambda function using a container image](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
