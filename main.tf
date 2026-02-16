terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }
}

# -----------------------------
# Provider
# -----------------------------
provider "azurerm" {
  features {}

  # REQUIRED for Jenkins Service Principal
  # Provider registration is done explicitly via Azure CLI in Jenkins
  skip_provider_registration = true
}

# -----------------------------
# Variables
# -----------------------------
variable "location" {
  # Azure requires lowercase, no spaces
  default = "westus2"
}

# -----------------------------
# Resource Group
# -----------------------------
resource "azurerm_resource_group" "rg" {
  name     = "demo-rg"
  location = var.location
}

# -----------------------------
# AKS Cluster
# -----------------------------
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "demo-aks"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "demoaks"

  # DO NOT pin kubernetes_version
  # Avoids preview API selection issues in Jenkins

  default_node_pool {
    name       = "system"
    node_count = 2
    vm_size    = "standard_dc48s_v3"
  }

  identity {
    type = "SystemAssigned"
  }

  role_based_access_control_enabled = true
  local_account_disabled            = false

  network_profile {
    network_plugin = "azure"
    load_balancer_sku = "standard"
  }

  tags = {
    environment = "demo"
  }
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