resource "cloudflare_pages_project" "blog" {
  account_id        = data.cloudflare_zone.zone.account_id
  name              = "simonko-dev-blog" # fixme, variable?
  production_branch = "main"

  build_config {
    build_command   = "hugo -b $CF_PAGES_URL"
    root_dir        = "blog"
    destination_dir = "public"
    build_caching   = true
  }

  deployment_configs {
    preview {
      environment_variables = {
        HUGO_VERSION = "0.145.0"
      }
    }
    production {
      environment_variables = {
        HUGO_VERSION = "0.145.0"
        CF_PAGES_URL = "https://${var.domain_name}"
      }
    }
  }

  source {
    type = "github"
    config {
      owner             = "SimonKO9"
      repo_name         = "simonko-dev-blog"
      production_branch = "main"
    }
  }


}

resource "cloudflare_pages_domain" "example_pages_domain" {
  for_each     = toset([var.domain_name, "www.${var.domain_name}"])
  account_id   = data.cloudflare_zone.zone.account_id
  project_name = cloudflare_pages_project.blog.name
  domain       = each.value
}
