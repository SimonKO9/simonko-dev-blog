---
title: "Starting a blog"
date: 2025-04-12
draft: false
ShowToc: true
tags: ["blog", "hugo", "automation", "cloudflare"]
---

## Preface

I started writing this post while my blog wasn't yet published. The idea of setting up a blog has been developing in me for a while now. Over the past few weeks I've gone through several posts on the topic on Reddit to, confronted the plan with my wife, as well as with Google Gemini and reached a point where I just needed to start doing.

I've bought the domain via Cloudflare and started setting up the blog locally. I am not a graphics designer or a frontend developer and I didn't want to spend too much time maintaining that. I wanted to focus on content and wanted to do it as cheap as possible, with least maintenance burden, as well as not need to worry about the security of underlying infrastructure. A statically generated website hosted somewhere sounded perfect. I settled on Cloudflare Pages, but there's plethora of options available: AWS Amplify, Netlify, Github Pages. Having the content of my website version controlled along the rest of the code sounded appealing to me as well.

I decided that documenting how I set up my blog may be a perfect candidate for my first post.

## Part 1: Bootstrapping the Hugo website

As a fan of containers, I decided to not pollute my environment with hugo binary and went with a containerized approach. I've created a container image based off ubuntu with hugo inside and used that to bootstrap my website following the guide on my theme's page (thank you [PaperMod](https://github.com/adityatelange/hugo-PaperMod)). I settled on a full copy of the theme by following the git clone option for the theme installation and removed `.git` and `.github` directory. I knew I'll want to customize the theme.

I used a default `hugo.yaml` as advertised in PaperMod's docs and started customizing it. Not everything is documented in the wiki, but it's easy to learn about the configuration options by looking inside the templates.

For example, I wanted to figure out which configuration option to use to modify the text in the nav section.
A quick look at `themes/PaperMod/layouts/partials/header.yml` revealed these lines:
```html
    <nav class="nav">
        <div class="logo">
            {{- $label_text := (site.Params.label.text | default site.Title) }}
            {{- if site.Title }}
```

by removing `params.label.text` from my Hugo configuration file I made sure `site.title` is used and that translates to the root `title` element of my config. See https://gohugo.io/methods/site/. I could have just updated params.label.text, but wanted to avoid duplicating it (DRY).

## Part 2: Writing your first post

Creating posts is a matter of creating markdown files under `content/posts/` directory:

```markdown
---
title: "Starting a blog"
date: 2025-04-12
draft: true
ShowToc: true
tags: ["blog", "hugo", "automation", "cloudflare"]
---
Hello, World!
```

Posts configured with `draft=true` will appear in your dev server, but won't be published until you change that property to false. We'll get to publishing later in this article.

Dev server can be started with `hugo server`. It binds to 127.0.0.1, and since I am running in a container, I had to change the bind to `0.0.0.0`.

For full reference, here's how I start my dev container:
```sh
# run the following to build:
# podman build . hugodev
podman run -it -p 1313:1313 -v .:/app hugodev

# then from within the container
hugo server --bind 0.0.0.0
```

## Part 3: Test publishing

I've built my website running `hugo` command, then followed the [guide on Cloudflare](https://developers.cloudflare.com/pages/framework-guides/deploy-a-hugo-site/).