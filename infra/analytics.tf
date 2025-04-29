resource "cloudflare_web_analytics_site" "example" {
  account_id   = data.cloudflare_zone.zone.account_id
  zone_tag     = data.cloudflare_zone.zone.zone_id
  auto_install = true
}