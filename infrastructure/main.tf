terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = "${var.prefix}-rg"
  location = var.location
}

# -----------------------------------------------------------------------------
# MySQL Flexible Server
# -----------------------------------------------------------------------------
resource "azurerm_mysql_flexible_server" "main" {
  name                   = "${var.prefix}-mysql"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  administrator_login    = "adminuser"
  administrator_password = var.mysql_admin_password
  sku_name               = "B_Standard_B1ms"
  version                = "8.0.21"

  storage {
    size_gb = 20
  }

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false
}

resource "azurerm_mysql_flexible_database" "monitoring" {
  name                = "monitoring_db"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_mysql_flexible_server.main.name
  charset             = "utf8mb4"
  collation           = "utf8mb4_unicode_ci"
}

# -----------------------------------------------------------------------------
# Key Vault
# -----------------------------------------------------------------------------
resource "azurerm_key_vault" "main" {
  name                       = "${var.prefix}-kv"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 90
  purge_protection_enabled   = false
}

# -----------------------------------------------------------------------------
# App Service Plan (Linux)
# -----------------------------------------------------------------------------
resource "azurerm_service_plan" "main" {
  name                = "${var.prefix}-plan"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  os_type             = "Linux"
  sku_name            = "B1"
}

# -----------------------------------------------------------------------------
# Backend App Service
# -----------------------------------------------------------------------------
resource "azurerm_linux_web_app" "backend" {
  name                = "${var.prefix}-api"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  service_plan_id     = azurerm_service_plan.main.id

  site_config {
    application_stack {
      docker_image_name   = "${var.prefix}acr.azurecr.io/backend:latest"
    }
  }

  app_settings = {
    DB_HOST             = azurerm_mysql_flexible_server.main.fqdn
    DB_USER             = "adminuser"
    DB_PASSWORD         = var.mysql_admin_password
    DB_NAME             = "monitoring_db"
    AZURE_KEY_VAULT_URL = azurerm_key_vault.main.vault_uri
  }
}

# -----------------------------------------------------------------------------
# Container App Environment + Monitoring Engine
# -----------------------------------------------------------------------------
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "main" {
  name                       = "${var.prefix}-cae"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_container_app" "monitoring_engine" {
  name                         = "${var.prefix}-engine"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  ingress {
    external_enabled = false
    target_port      = 8001

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  template {
    container {
      name   = "monitoring-engine"
      image  = "${var.prefix}acr.azurecr.io/monitoring-engine:latest"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name  = "BACKEND_API_URL"
        value = "https://${azurerm_linux_web_app.backend.default_hostname}/api/v1"
      }
    }

    min_replicas = 0
    max_replicas = 5
  }
}

# -----------------------------------------------------------------------------
# Azure Functions (Scheduler)
# -----------------------------------------------------------------------------
resource "azurerm_storage_account" "functions" {
  name                     = "${var.prefix}funcsa"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_linux_function_app" "scheduler" {
  name                       = "${var.prefix}-scheduler"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME = "python"
    BACKEND_API_URL          = "https://${azurerm_linux_web_app.backend.default_hostname}/api/v1"
    MONITORING_ENGINE_URL    = "https://${azurerm_container_app.monitoring_engine.ingress[0].fqdn}"
  }
}

# -----------------------------------------------------------------------------
# Application Insights
# -----------------------------------------------------------------------------
resource "azurerm_application_insights" "main" {
  name                = "${var.prefix}-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  application_type    = "web"
}

# -----------------------------------------------------------------------------
# Communication Services (Email)
# -----------------------------------------------------------------------------
resource "azurerm_communication_service" "main" {
  name                = "${var.prefix}-comm"
  resource_group_name = azurerm_resource_group.main.name
  data_location       = "United States"
}
