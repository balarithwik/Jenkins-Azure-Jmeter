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

variable "ssh_private_key_path" {
  default = "C:/Users/Bala/.ssh/id_rsa"
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
# Linux VM
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

  depends_on = [
    azurerm_network_interface_security_group_association.assoc
  ]

  provisioner "remote-exec" {
    inline = [
      "set -e",

      "sudo apt-get update -y",

      "sudo swapoff -a",
      "sudo sed -i '/ swap / s/^/#/' /etc/fstab",

      "sudo modprobe overlay",
      "sudo modprobe br_netfilter",

      "sudo tee /etc/sysctl.d/k8s.conf <<EOF\nnet.bridge.bridge-nf-call-iptables=1\nnet.bridge.bridge-nf-call-ip6tables=1\nnet.ipv4.ip_forward=1\nEOF",
      "sudo sysctl --system",

      "sudo apt-get install -y containerd",
      "sudo mkdir -p /etc/containerd",
      "sudo containerd config default | sudo tee /etc/containerd/config.toml",
      "sudo systemctl restart containerd",
      "sudo systemctl enable containerd",

      "sudo apt-get install -y apt-transport-https ca-certificates curl",
      "sudo mkdir -p /etc/apt/keyrings",
      "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes.gpg",
      "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes.gpg] https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list",

      "sudo apt-get update -y",
      "sudo apt-get install -y kubelet kubeadm kubectl",
      "sudo apt-mark hold kubelet kubeadm kubectl",

      "sudo kubeadm init --pod-network-cidr=10.244.0.0/16 || true",

      "mkdir -p /home/${var.admin_username}/.kube",
      "sudo cp /etc/kubernetes/admin.conf /home/${var.admin_username}/.kube/config",
      "sudo chown ${var.admin_username}:${var.admin_username} /home/${var.admin_username}/.kube/config",

      "kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml",

      "kubectl taint nodes --all node-role.kubernetes.io/control-plane- || true",

      "echo 'Terraform Kubernetes bootstrap completed'"
    ]

    connection {
      type        = "ssh"
      user        = var.admin_username
      private_key = file(var.ssh_private_key_path)
      host        = azurerm_public_ip.vm_ip.ip_address
      timeout     = "45m"
    }
  }
}

# --------------------------------------------------
# Outputs
# --------------------------------------------------
output "vm_public_ip" {
  value = azurerm_public_ip.vm_ip.ip_address
}