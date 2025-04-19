resource "cloudflare_record" "root" {
  zone_id = data.cloudflare_zone.zone.zone_id
  ttl     = 1 # auto
  type    = "CNAME"
  name    = "simonko.dev"
  content = "simonko-dev-blog.pages.dev"
  proxied = true
}

resource "cloudflare_record" "www" {
  zone_id = data.cloudflare_zone.zone.zone_id
  ttl     = 1 # auto
  type    = "CNAME"
  name    = "www"
  content = "simonko-dev-blog.pages.dev"
  proxied = true
}

