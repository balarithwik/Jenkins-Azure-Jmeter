terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.64.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id            = "c3e1d504-633c-4752-b82f-7af3da9f2fc1"
  tenant_id                  = "7b8e0a9a-8ff5-4d1e-a54f-a0f4d0664488"
  skip_provider_registration = true
}

resource "azurerm_resource_group" "rg" {
  name     = "demo-rg"
  location = "West US 2"
}

resource "azurerm_virtual_network" "vnet" {
  name                = "demo-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
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
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_network_interface" "nic" {
  name                = "demo-nic"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.vm_ip.id
  }
}

resource "azurerm_network_security_group" "nsg" {
  name                = "demo-nsg"
  location            = azurerm_resource_group.rg.location
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

resource "azurerm_network_interface_security_group_association" "assoc" {
  network_interface_id      = azurerm_network_interface.nic.id
  network_security_group_id = azurerm_network_security_group.nsg.id
}

resource "azurerm_linux_virtual_machine" "vm" {
  name                = "demo-vm"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  size                = "Standard_D4s_v3"
  admin_username      = "azureuser"

  network_interface_ids = [azurerm_network_interface.nic.id]

  admin_ssh_key {
    username   = "azureuser"
    public_key = file("C:/Users/Bala/.ssh/id_rsa.pub")
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

  provisioner "remote-exec" {
    inline = [
      "set -e",

      # ---- Base packages ----
      "sudo apt-get update -y",
      "sudo apt-get install -y ca-certificates curl gnupg lsb-release",

      # ---- Docker repo + install ----
      "curl -fsSL https://get.docker.com | sudo sh",
      "sudo systemctl enable docker",
      "sudo systemctl start docker",

      # ---- Kubernetes repo ----
      "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/kubernetes.gpg",
      "echo 'deb [signed-by=/etc/apt/trusted.gpg.d/kubernetes.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list",

      "sudo apt-get update -y",
      "sudo apt-get install -y kubelet kubeadm kubectl",
      "sudo apt-mark hold kubelet kubeadm kubectl",

      # ---- containerd config for Kubernetes ----
      "sudo mkdir -p /etc/containerd",
      "containerd config default | sudo tee /etc/containerd/config.toml",
      "sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml",
      "sudo systemctl restart containerd",
      "sudo systemctl restart docker",

      # ---- kubeadm init (safe) ----
      "if [ ! -f /etc/kubernetes/admin.conf ]; then sudo kubeadm init --pod-network-cidr=10.244.0.0/16; fi",

      # ---- kubeconfig ----
      "if [ -f /etc/kubernetes/admin.conf ]; then mkdir -p /home/azureuser/.kube; sudo cp /etc/kubernetes/admin.conf /home/azureuser/.kube/config; sudo chown azureuser:azureuser /home/azureuser/.kube/config; fi",

      # ---- Flannel network ----
      "kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml || true",
      "sleep 30",

      # ---- Allow scheduling ----
      "kubectl taint nodes --all node-role.kubernetes.io/control-plane- || true",

      # ---- Deploy Nginx ----
      "kubectl create deployment nginx --image=nginx || true",
      "kubectl expose deployment nginx --type=NodePort --port=80 || true",

      # ---- Deploy MySQL ----
      "kubectl create deployment mysql --image=mysql:5.7 || true",
      "kubectl set env deployment/mysql MYSQL_ROOT_PASSWORD=rootpass || true",
      "kubectl expose deployment mysql --type=NodePort --port=3306 || true",

      # ---- Status ----
      "kubectl get nodes || true",
      "kubectl get svc || true"
    ]

    connection {
      type        = "ssh"
      user        = "azureuser"
      private_key = file("C:/Users/Bala/.ssh/id_rsa")
      host        = azurerm_public_ip.vm_ip.ip_address
      timeout     = "30m"
    }
  }
}

output "vm_public_ip" {
  value = azurerm_public_ip.vm_ip.ip_address
}