data "cloudflare_zone" "zone" {
  name = var.domain_name
}