pipeline {
  agent any

  environment {
    ARM_CLIENT_ID       = credentials('ARM_CLIENT_ID')
    ARM_CLIENT_SECRET   = credentials('ARM_CLIENT_SECRET')
    ARM_SUBSCRIPTION_ID = credentials('ARM_SUBSCRIPTION_ID')
    ARM_TENANT_ID       = credentials('ARM_TENANT_ID')

    SSH_USER = "azureuser"
    TF_IN_AUTOMATION = "true"
  }

  stages {

    stage('Checkout Code') {
      steps {
        git branch: 'main',
            url: 'https://github.com/balarithwik/Jenkins-Azure-Jmeter.git'
      }
    }

    stage('Terraform Init') {
      steps {
        bat 'terraform init'
      }
    }

    stage('Terraform Apply') {
      steps {
        bat 'terraform apply -auto-approve'
      }
    }

    stage('Fetch VM Public IP') {
      steps {
        script {
          env.VM_IP = bat(
            script: 'terraform output -raw vm_public_ip',
            returnStdout: true
          ).trim()
        }
        echo "VM IP: ${env.VM_IP}"
      }
    }

    stage('Install NGINX & Create HTML Pages') {
      steps {
        withCredentials([string(credentialsId: 'azure-token', variable: 'SSH_KEY')]) {
          writeFile file: 'id_rsa', text: SSH_KEY
          bat 'chmod 600 id_rsa'

          bat """
          ssh -i id_rsa -o StrictHostKeyChecking=no %SSH_USER%@%VM_IP% ^
          "sudo apt update &&
           sudo rm -rf /var/www/html/* &&

           echo '<h1>Home Page</h1>'   | sudo tee /var/www/html/index.html &&
           echo '<h1>About Page</h1>'  | sudo tee /var/www/html/about.html &&
           echo '<h1>Contact Page</h1>'| sudo tee /var/www/html/contact.html &&

           sudo systemctl restart nginx"
          """
        }
      }
    }

    stage('Install Java & JMeter') {
      steps {
        withCredentials([string(credentialsId: 'azure-token', variable: 'SSH_KEY')]) {
          writeFile file: 'id_rsa', text: SSH_KEY
          bat 'chmod 600 id_rsa'

          bat """
          ssh -i id_rsa -o StrictHostKeyChecking=no %SSH_USER%@%VM_IP% ^
          "sudo apt install -y openjdk-11-jdk wget unzip zip &&
           wget https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.3.tgz &&
           tar -xzf apache-jmeter-5.6.3.tgz"
          """
        }
      }
    }

    stage('Copy JMeter Test File') {
      steps {
        withCredentials([string(credentialsId: 'azure-token', variable: 'SSH_KEY')]) {
          writeFile file: 'id_rsa', text: SSH_KEY
          bat 'chmod 600 id_rsa'

          bat """
          scp -i id_rsa -o StrictHostKeyChecking=no web_perf_test.jmx ^
          %SSH_USER%@%VM_IP%:/home/azureuser/
          """
        }
      }
    }

    stage('Run JMeter Test & Zip Report') {
      steps {
        withCredentials([string(credentialsId: 'azure-token', variable: 'SSH_KEY')]) {
          writeFile file: 'id_rsa', text: SSH_KEY
          bat 'chmod 600 id_rsa'

          bat """
          ssh -i id_rsa -o StrictHostKeyChecking=no %SSH_USER%@%VM_IP% ^
          "/home/azureuser/apache-jmeter-5.6.3/bin/jmeter -n \
           -t /home/azureuser/web_perf_test.jmx \
           -l results.jtl \
           -e -o report &&
           zip -r jmeter-report.zip report"
          """
        }
      }
    }

    stage('Copy Report to Jenkins') {
      steps {
        withCredentials([string(credentialsId: 'azure-token', variable: 'SSH_KEY')]) {
          writeFile file: 'id_rsa', text: SSH_KEY
          bat 'chmod 600 id_rsa'

          bat """
          scp -i id_rsa -o StrictHostKeyChecking=no ^
          %SSH_USER%@%VM_IP%:/home/azureuser/jmeter-report.zip .
          """
        }
      }
    }

    stage('Email JMeter Report') {
      steps {
        emailext(
          subject: "JMeter Report | Build #${BUILD_NUMBER}",
          body: """
          Hi Team,

          JMeter test executed successfully against NGINX.

          HTML report is attached as ZIP.

          Build URL:
          ${BUILD_URL}

          Regards,
          Jenkins
          """,
          to: "rithwik10122000@gmail.com",
          attachmentsPattern: "jmeter-report.zip"
        )
      }
    }
  }

  post {
    always {
      echo "Destroying infrastructure (mandatory cleanup)"
      bat 'terraform destroy -auto-approve'
    }
  }
}