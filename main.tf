terraform {
  required_version = ">= 1.3.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 3.64.0"
    }
  }
}

# --------------------------------------------------
# Provider
# --------------------------------------------------
provider "azurerm" {
  features {}
  skip_provider_registration = true
}

# --------------------------------------------------
# Variables
# --------------------------------------------------
variable "location" {
  default = "West US 2"
}

variable "admin_username" {
  default = "azureuser"
}

variable "ssh_public_key_path" {
  default = "C:/Users/Bala/.ssh/id_rsa.pub"
}

# --------------------------------------------------
# Resource Group
# --------------------------------------------------
resource "azurerm_resource_group" "rg" {
  name     = "demo-rg"
  location = var.location
}

# --------------------------------------------------
# Networking
# --------------------------------------------------
resource "azurerm_virtual_network" "vnet" {
  name                = "demo-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_subnet" "subnet" {
  name                 = "demo-subnet"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

resource "azurerm_public_ip" "vm_ip" {
  name                = "vm-public-ip"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_security_group" "nsg" {
  name                = "demo-nsg"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "NodePort"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "30000-32767"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "nic" {
  name                = "demo-nic"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm_ip.id
  }
}

resource "azurerm_network_interface_security_group_association" "assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

# --------------------------------------------------
# Linux VM (cloud-init)
# --------------------------------------------------
resource "azurerm_linux_virtual_machine" "vm" {
  name                = "demo-vm"
  resource_group_name = azurerm_resource_group.rg.name
  location            = var.location
  size                = "Standard_D4s_v3"
  admin_username      = var.admin_username

  network_interface_ids = [
    azurerm_network_interface.nic.id
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts-gen2"
    version   = "latest"
  }

  # 👇 Cloud-init replaces remote-exec
  custom_data = base64encode(file("${path.module}/cloud-init.yaml"))

  depends_on = [
    azurerm_network_interface_security_group_association.assoc
  ]
}

# --------------------------------------------------
# Outputs
# --------------------------------------------------
output "vm_public_ip" {
  value = azurerm_public_ip.vm_ip.ip_address
}