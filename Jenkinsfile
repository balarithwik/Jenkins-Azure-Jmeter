pipeline {
  agent any

  environment {
    ARM_CLIENT_ID       = credentials('ARM_CLIENT_ID')
    ARM_CLIENT_SECRET   = credentials('ARM_CLIENT_SECRET')
    ARM_SUBSCRIPTION_ID = credentials('ARM_SUBSCRIPTION_ID')
    ARM_TENANT_ID       = credentials('ARM_TENANT_ID')

    SSH_USER = "azureuser"
    TF_IN_AUTOMATION = "true"
    SSH_OPTS = "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
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
        bat 'terraform init -input=false'
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
        echo "VM IP fetched: ${env.VM_IP}"
      }
    }

    stage('Wait for SSH') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          for /L %%i in (1,1,30) do (
            ssh -i %SSH_KEY% %SSH_OPTS% %SSH_USER%@%VM_IP% "echo SSH ready" && exit /b 0
            timeout /t 15 >nul
          )
          exit /b 1
          """
        }
      }
    }

    stage('Wait for Kubernetes') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          ssh -i %SSH_KEY% %SSH_OPTS% %SSH_USER%@%VM_IP% ^
          "until kubectl get nodes; do echo waiting for k8s; sleep 15; done"
          """
        }
      }
    }

    stage('Deploy NGINX & MySQL (Kubernetes)') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          scp -r -i %SSH_KEY% %SSH_OPTS% k8s %SSH_USER%@%VM_IP%:/home/azureuser/
          ssh -i %SSH_KEY% %SSH_OPTS% %SSH_USER%@%VM_IP% ^
          "kubectl apply -f k8s/nginx-configmap.yaml &&
           kubectl apply -f k8s/nginx-deployment.yaml &&
           kubectl apply -f k8s/mysql-deployment.yaml"
          """
        }
      }
    }

    stage('Install Java & JMeter') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          ssh -i %SSH_KEY% %SSH_OPTS% %SSH_USER%@%VM_IP% ^
          "sudo apt-get update &&
           sudo apt-get install -y openjdk-11-jdk wget unzip &&
           if [ ! -d apache-jmeter-5.6.3 ]; then
             wget https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.3.tgz &&
             tar -xzf apache-jmeter-5.6.3.tgz;
           fi"
          """
        }
      }
    }

    stage('Copy JMeter Test File') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          scp -i %SSH_KEY% %SSH_OPTS% jmeter/web_perf_test.jmx ^
          %SSH_USER%@%VM_IP%:/home/azureuser/
          """
        }
      }
    }

    stage('Run JMeter Test & Generate Report') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          ssh -i %SSH_KEY% %SSH_OPTS% %SSH_USER%@%VM_IP% ^
          "/home/azureuser/apache-jmeter-5.6.3/bin/jmeter -n ^
           -t /home/azureuser/web_perf_test.jmx ^
           -JHOST=%VM_IP% ^
           -JPORT=30080 ^
           -l results.jtl ^
           -e -o report &&
           zip -r jmeter-report.zip report"
          """
        }
      }
    }

    stage('Copy Report to Jenkins') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          scp -i %SSH_KEY% %SSH_OPTS% ^
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

JMeter performance test executed successfully.

Target:
http://${VM_IP}:30080

Report attached.

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
      echo "Destroying infrastructure"
      bat 'terraform destroy -auto-approve'
    }
  }
}