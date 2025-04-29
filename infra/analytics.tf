# requires separate READ and EDIT permissions for account analytics, as well as READ zone analytics
resource "cloudflare_web_analytics_site" "analytics" {
  account_id   = data.cloudflare_zone.zone.account_id
  zone_tag     = data.cloudflare_zone.zone.zone_id
  auto_install = true
}