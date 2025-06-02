---
title: "How to configure redirect from www to non-www in Cloudflare using Terraform"
date: 2025-06-02
draft: false
ShowToc: true
tags: ["blog", "hugo", "automation", "cloudflare", "terraform", "SEO"]
---

## Preface

I ran a bunch of tools to check if my blog is SEO-friendly. One of the recommendation was to canonicalize the URLs by avoiding multiple addresses pointing to the same page. In my case, that was serving my website at both https://www.simonko.dev, as well as https://simonko.dev. The solution is rather simple - redirect www to non-www. My website is fully configured using Terraform. Since I've never done it before with Cloudflare Terraform provider, I thought I might share what I did.

I am not using the latest version of the provider due to a bug, as described in [my blog post about how I automated my blog](/posts/blog-setup-automation), so depending on the version you use, it may be slightly different, but the principle remains.


## The implementation

In Cloudflare, the redirect is achieved by defining a Cloudflare Pages Rule. The rule is supposed to match `www.simonko.dev/*`, and, if that matches, respond with a 301 and a redirect to `simonko.dev/$1`, where `$1` is the matched wildcard piece.

Here's how it's done with Terraform:

```terraform

# optional data source
data "cloudflare_zone" "zone" {
  name = var.domain_name # var.domain_name = simonko.dev
}

resource "cloudflare_page_rule" "www_to_non_www_redirect" {
  zone_id = data.cloudflare_zone.zone.zone_id # or replace with your zone id
  target  = "www.${var.domain_name}/*"

  actions {
    forwarding_url {
      url        = "https://${var.domain_name}/$1"
      status_code = 301
    }
  }

  priority = 1
  status   = "active"
}
```

Please note that this operation requires `Zone - Page Rules - Edit` permissions granted for your token, otherwise you may get an error like the one I got:
```
Error: failed to create page rule: Unauthorized to access requested resource (9109)

  with cloudflare_page_rule.www_to_non_www_redirect,
  on pagerules.tf line 1, in resource "cloudflare_page_rule" "www_to_non_www_redirect":
   1: resource "cloudflare_page_rule" "www_to_non_www_redirect" {
```

...and that's really all there's to it. 

I'm keeping this post short.

## Validation

Once configured, I ran a few checks to confirm the rule is working as expected:

```sh
# Test redirect at root
$ curl --head https://www.simonko.dev 
HTTP/2 301 
date: Mon, 02 Jun 2025 19:36:40 GMT
location: https://simonko.dev/
# ...

# Test redirect for a specific page
$ curl --head -s https://www.simonko.dev/posts/blog-setup-automation/
HTTP/2 301 
date: Mon, 02 Jun 2025 19:38:34 GMT
location: https://simonko.dev/posts/blog-setup-automation/
# ...

# Test no redirect if non-www domain is used
$ curl --head -s https://simonko.dev/posts/blog-setup-automation/    
HTTP/2 200 
date: Mon, 02 Jun 2025 19:39:32 GMT
content-type: text/html; charset=utf-8
```

## Additional comment

Some SEO-checkers classified this problem as "Duplicate content", where they could access my posts using either www or non-www domain. Others called this "canonicalization issues". The explanation provided by these tools is that some search engines may be "unsure" about which is the correct one to index. I am not sure if this was a problem in practice, as the links on my blog always pointed to a non-www version, regardless of the URL used to access the page. Yet, I decided to fix it to get a higher score, he-he - and to make sure it doesn't become a problem in future. ;)