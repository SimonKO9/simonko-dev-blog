resource "cloudflare_page_rule" "www_to_non_www_redirect" {
  zone_id = data.cloudflare_zone.zone.zone_id
  target  = "www.${var.domain_name}/*"

  actions {
    forwarding_url {
      url         = "https://${var.domain_name}/$1"
      status_code = 301
    }
  }

  priority = 1
  status   = "active"
}
