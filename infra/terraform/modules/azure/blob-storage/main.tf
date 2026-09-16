resource "azurerm_resource_group" "this" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location
}

resource "azurerm_storage_account" "this" {
  name                     = lower(replace("${var.project_name}${var.environment}", "-", ""))
  resource_group_name      = azurerm_resource_group.this.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  blob_properties {
    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["PUT", "GET", "POST"]
      allowed_origins    = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://urban-chainsaw-r49qv7gvx57c955-5500.app.github.dev",
        "https://tricloudvault.charansai.me",
        "https://charansai.me"
      ]
      exposed_headers    = ["ETag"]
      max_age_in_seconds = 3600
    }
  }
}

resource "azurerm_storage_container" "tricloud_container" {
  name                  = "tricloud-vault"
  storage_account_name  = azurerm_storage_account.this.name
  container_access_type = "private"
}

