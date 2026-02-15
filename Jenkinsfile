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

    /* ✅ FIX 1: Proper cloud-init + SSH readiness */
    stage('Wait for SSH') {
  steps {
    withCredentials([sshUserPrivateKey(
      credentialsId: 'azure-token',
      keyFileVariable: 'SSH_KEY'
    )]) {
      bat """
      echo Waiting for SSH...
      for /L %%i in (1,1,20) do (
        ssh -i %SSH_KEY% -o StrictHostKeyChecking=no -o ConnectTimeout=10 %SSH_USER%@%VM_IP% "echo SSH OK" && exit /b 0
        echo Retry %%i...
        timeout /t 15 >nul
      )
      exit /b 1
      """
    }
  }
}

    stage('Install NGINX & Create HTML Pages') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          ssh -i %SSH_KEY% %SSH_OPTS% %SSH_USER%@%VM_IP% ^
          "sudo apt-get update -y &&
           sudo apt-get install -y nginx &&
           sudo rm -rf /var/www/html/* &&
           echo '<h1>Home Page</h1>'    | sudo tee /var/www/html/index.html &&
           echo '<h1>About Page</h1>'   | sudo tee /var/www/html/about.html &&
           echo '<h1>Contact Page</h1>' | sudo tee /var/www/html/contact.html &&
           sudo systemctl enable nginx &&
           sudo systemctl restart nginx"
          """
        }
      }
    }

    /* ✅ FIX 2: Idempotent Java + JMeter install */
    stage('Install Java & JMeter') {
      steps {
        withCredentials([sshUserPrivateKey(
          credentialsId: 'azure-token',
          keyFileVariable: 'SSH_KEY'
        )]) {
          bat """
          ssh -i %SSH_KEY% %SSH_OPTS% %SSH_USER%@%VM_IP% ^
          "sudo apt-get install -y openjdk-11-jdk wget unzip zip &&
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
          scp -i %SSH_KEY% %SSH_OPTS% ^
          web_perf_test.jmx %SSH_USER%@%VM_IP%:/home/azureuser/
          """
        }
      }
    }

    /* ✅ FIX 3: Explicit HOST injection (no confusion) */
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

Target Host:
${VM_IP}

HTML report is attached.

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

  /* ✅ FIX 4: Guaranteed cleanup */
  post {
    always {
      echo "Destroying infrastructure (mandatory cleanup)"
      bat 'terraform destroy -auto-approve'
    }
  }
}