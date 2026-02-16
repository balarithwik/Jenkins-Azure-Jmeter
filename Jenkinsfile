pipeline {
  agent any

  environment {
    ARM_CLIENT_ID       = credentials('ARM_CLIENT_ID')
    ARM_CLIENT_SECRET   = credentials('ARM_CLIENT_SECRET')
    ARM_SUBSCRIPTION_ID = credentials('ARM_SUBSCRIPTION_ID')
    ARM_TENANT_ID       = credentials('ARM_TENANT_ID')

    TF_IN_AUTOMATION = "true"

    JAVA_HOME   = "C:\\Java\\jdk-11"
    JMETER_HOME = "C:\\JMeter\\apache-jmeter-5.6.3"
    PATH = "${JAVA_HOME}\\bin;${JMETER_HOME}\\bin;${env.PATH}"
  }

  stages {

    stage('Checkout Code') {
      steps {
        git branch: 'main',
            url: 'https://github.com/balarithwik/Jenkins-Azure-Jmeter.git'
      }
    }

    stage('Azure Login & Provider Registration') {
      steps {
        bat '''
        az login --service-principal ^
          -u %ARM_CLIENT_ID% ^
          -p %ARM_CLIENT_SECRET% ^
          --tenant %ARM_TENANT_ID%

        az account set --subscription %ARM_SUBSCRIPTION_ID%

        az provider register --namespace Microsoft.ContainerService
        az provider register --namespace Microsoft.Compute
        az provider register --namespace Microsoft.Network
        az provider register --namespace Microsoft.Storage

        timeout /t 30
        '''
      }
    }

    stage('Terraform Init') {
      steps {
        bat 'terraform init -upgrade -input=false'
      }
    }

    stage('Terraform Apply') {
      steps {
        bat 'terraform apply -auto-approve'
      }
    }

    stage('Configure Kubernetes Access') {
      steps {
        bat '''
        az aks get-credentials ^
          --resource-group demo-rg ^
          --name demo-aks ^
          --overwrite-existing
        '''
      }
    }

    stage('Wait for Kubernetes Ready') {
      steps {
        bat '''
        kubectl get nodes
        kubectl wait --for=condition=Ready nodes --all --timeout=600s
        '''
      }
    }

    stage('Deploy NGINX & MySQL') {
      steps {
        bat '''
        kubectl apply -f k8s/nginx-configmap.yaml
        kubectl apply -f k8s/mysql-deployment.yaml
        kubectl apply -f k8s/nginx-deployment.yaml
        '''
      }
    }

    stage('Wait for NGINX LoadBalancer IP') {
      steps {
        powershell '''
$ip = ""
for ($i = 0; $i -lt 40; $i++) {
  try {
    $svc = kubectl get svc nginx -o json | ConvertFrom-Json
    $ip = $svc.status.loadBalancer.ingress[0].ip
    if ($ip) {
      Set-Content app_ip.txt $ip
      exit 0
    }
  } catch {}
  Start-Sleep 10
}
throw "Failed to get LoadBalancer IP"
'''
        bat '''
        set /p APP_IP=<app_ip.txt
        echo Application URL: http://%APP_IP%
        '''
      }
    }

    /* ============================
       JAVA & JMETER INSTALL STEPS
       ============================ */

    stage('Install Java (if not exists)') {
      steps {
        powershell '''
if (!(Test-Path "C:\\Java\\jdk-11")) {
  Write-Host "Installing Java 11..."
  Invoke-WebRequest `
    -Uri https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.22%2B7/OpenJDK11U-jdk_x64_windows_hotspot_11.0.22_7.zip `
    -OutFile java.zip
  Expand-Archive java.zip C:\\Java -Force
  Rename-Item C:\\Java\\jdk-11* C:\\Java\\jdk-11
} else {
  Write-Host "Java already installed"
}
'''
      }
    }

    stage('Install JMeter (if not exists)') {
      steps {
        powershell '''
if (!(Test-Path "C:\\JMeter\\apache-jmeter-5.6.3")) {
  Write-Host "Installing Apache JMeter..."
  Invoke-WebRequest `
    -Uri https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.3.zip `
    -OutFile jmeter.zip
  Expand-Archive jmeter.zip C:\\JMeter -Force
} else {
  Write-Host "JMeter already installed"
}
'''
      }
    }

    stage('Verify Java & JMeter') {
      steps {
        bat '''
        java -version
        jmeter -v
        '''
      }
    }

    /* ============================
       JMETER EXECUTION
       ============================ */

    stage('Run JMeter Test (Docker)') {
      steps {
        bat '''
        docker run --rm ^
          -v %CD%\\jmeter:/jmeter ^
          -v %CD%\\jmeter-report:/report ^
          justb4/jmeter:5.6.3 ^
          -n ^
          -t /jmeter/web_perf_test.jmx ^
          -JHOST=%APP_IP% ^
          -l /report/results.jtl ^
          -e -o /report/html
        '''
      }
    }

    stage('Zip JMeter Report') {
      steps {
        bat '''
        powershell Compress-Archive ^
          jmeter-report/html ^
          jmeter-report.zip ^
          -Force
        '''
      }
    }

    stage('Email JMeter Report') {
      steps {
        emailext(
          subject: "JMeter Report | Build #${BUILD_NUMBER}",
          body: """
Hi Team,

Performance testing completed successfully.

Target URL:
http://${APP_IP}

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
      echo "Destroying Azure infrastructure"
      bat 'terraform destroy -auto-approve'
    }
  }
}