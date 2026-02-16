terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 3.64.0"
    }
  }
}

# -----------------------------
# Provider
# -----------------------------
provider "azurerm" {
  features {}

  # IMPORTANT:
  # Must be false in Jenkins so AKS provider gets registered
  skip_provider_registration = false
}

# -----------------------------
# Variables
# -----------------------------
variable "location" {
  # Azure prefers lowercase, no spaces
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

  default_node_pool {
    name       = "system"
    node_count = 2
    vm_size    = "Standard_DS2_v2"
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"
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