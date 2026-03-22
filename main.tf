terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

# -----------------------------
# Provider
# -----------------------------
provider "azurerm" {
  features {}
  skip_provider_registration = true
}

# -----------------------------
# Variables
# -----------------------------
variable "location" {
  default = "westus2"
}

# -----------------------------
# Random suffix for ACR name
# -----------------------------
resource "random_string" "acr_suffix" {
  length  = 6
  upper   = false
  special = false
  numeric = true
}

# -----------------------------
# Resource Group
# -----------------------------
resource "azurerm_resource_group" "rg" {
  name     = "demo-rg"
  location = var.location
}

# -----------------------------
# Azure Container Registry
# -----------------------------
resource "azurerm_container_registry" "acr" {
  name                = "demoacr${random_string.acr_suffix.result}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = {
    environment = "demo"
  }
}

# -----------------------------
# AKS Cluster
# -----------------------------
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "demo-aks"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "demoaks"

  default_node_pool {
    name       = "system"
    node_count = 2
    vm_size    = "Standard_B2s_v2"
  }

  identity {
    type = "SystemAssigned"
  }

  role_based_access_control_enabled = true
  local_account_disabled            = false

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
  }

  tags = {
    environment = "demo"
  }
}

# -----------------------------
# Grant AKS pull access to ACR
# -----------------------------
resource "azurerm_role_assignment" "aks_acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# -----------------------------
# Outputs
# -----------------------------
output "aks_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

output "resource_group" {
  value = azurerm_resource_group.rg.name
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "acr_admin_username" {
  value = azurerm_container_registry.acr.admin_username
  sensitive = true
}

output "acr_admin_password" {
  value = azurerm_container_registry.acr.admin_password
  sensitive = true
}