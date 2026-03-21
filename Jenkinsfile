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

    DOCKERHUB_REPO = "balarithwik"
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

    stage('Build Backend Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          bat '''
          docker login -u %DOCKER_USER% -p %DOCKER_PASS%
          docker build -t %DOCKER_USER%/retail-backend:latest backend
          docker push %DOCKER_USER%/retail-backend:latest
          '''
        }
      }
    }

    stage('Deploy MySQL & Backend') {
      steps {
        bat '''
        kubectl apply -f k8s/mysql-secret.yaml
        kubectl apply -f k8s/mysql-init-configmap.yaml
        kubectl apply -f k8s/mysql-service.yaml
        kubectl apply -f k8s/mysql-deployment.yaml
        kubectl apply -f k8s/backend-service.yaml
        kubectl apply -f k8s/backend-deployment.yaml
        '''
      }
    }

    stage('Wait for Backend LoadBalancer IP') {
      steps {
        script {
          def ip = powershell(
            returnStdout: true,
            script: '''
$ip = ""
for ($i = 0; $i -lt 40; $i++) {
  try {
    $svc = kubectl get svc retail-backend -o json | ConvertFrom-Json
    $ip = $svc.status.loadBalancer.ingress[0].ip
    if ($ip) {
      Write-Output $ip
      exit 0
    }
  } catch {
    Write-Host "Waiting for Backend LoadBalancer IP..."
  }
  Start-Sleep -Seconds 10
}
throw "Failed to get Backend LoadBalancer IP"
'''
          ).trim()

          env.BACKEND_IP = ip
          echo "Backend URL: http://${env.BACKEND_IP}:5000"
        }
      }
    }

    stage('Patch Frontend API URL') {
      steps {
        powershell """
        \$filePath = "frontend\\src\\App.js"
        \$content = Get-Content \$filePath -Raw
        \$updated = \$content -replace 'const API_BASE = .*?;', 'const API_BASE = "http://${env.BACKEND_IP}:5000";'
        Set-Content -Path \$filePath -Value \$updated
        """
      }
    }

    stage('Build Frontend Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          bat '''
          docker login -u %DOCKER_USER% -p %DOCKER_PASS%
          docker build -t %DOCKER_USER%/retail-frontend:latest frontend
          docker push %DOCKER_USER%/retail-frontend:latest
          '''
        }
      }
    }

    stage('Deploy Frontend') {
      steps {
        bat '''
        kubectl apply -f k8s/frontend-service.yaml
        kubectl apply -f k8s/frontend-deployment.yaml
        '''
      }
    }

    stage('Wait for Deployments Ready') {
      steps {
        bat '''
        kubectl rollout status deployment/mysql --timeout=300s
        kubectl rollout status deployment/retail-backend --timeout=300s
        kubectl rollout status deployment/retail-frontend --timeout=300s
        kubectl get pods
        kubectl get svc
        '''
      }
    }

    stage('Wait for Frontend LoadBalancer IP') {
      steps {
        script {
          def ip = powershell(
            returnStdout: true,
            script: '''
$ip = ""
for ($i = 0; $i -lt 40; $i++) {
  try {
    $svc = kubectl get svc retail-frontend -o json | ConvertFrom-Json
    $ip = $svc.status.loadBalancer.ingress[0].ip
    if ($ip) {
      Write-Output $ip
      exit 0
    }
  } catch {
    Write-Host "Waiting for Frontend LoadBalancer IP..."
  }
  Start-Sleep -Seconds 10
}
throw "Failed to get Frontend LoadBalancer IP"
'''
          ).trim()

          env.FRONTEND_IP = ip
          echo "Frontend URL: http://${env.FRONTEND_IP}"
        }
      }
    }

    stage('Validate Application Endpoints') {
      steps {
        bat """
        echo Validating Backend Health
        curl -f http://${BACKEND_IP}:5000/health || exit 1

        echo Validating Backend Products
        curl -f http://${BACKEND_IP}:5000/products || exit 1

        echo Validating Frontend Page
        curl -f http://${FRONTEND_IP} || exit 1
        """
      }
    }

    stage('Install Java (if not exists)') {
      steps {
        powershell '''
$javaHome = "C:\\Java\\jdk-11"

if (!(Test-Path $javaHome)) {
  Write-Host "Installing Java 11..."

  $zip = "java.zip"
  $url = "https://github.com/adoptium/temurin11-binaries/releases/download/jdk-11.0.22%2B7/OpenJDK11U-jdk_x64_windows_hotspot_11.0.22_7.zip"

  Invoke-WebRequest -Uri $url -OutFile $zip
  Expand-Archive $zip C:\Java -Force

  $extracted = Get-ChildItem C:\Java | Where-Object { $_.Name -like "jdk-11*" } | Select-Object -First 1

  if ($null -eq $extracted) {
    throw "JDK extraction failed"
  }

  Rename-Item $extracted.FullName $javaHome
  Write-Host "Java installed successfully"
}
else {
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
  Invoke-WebRequest -Uri https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.3.zip -OutFile jmeter.zip
  Expand-Archive jmeter.zip C:\JMeter -Force
}
else {
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

    stage('Run JMeter Test') {
      steps {
        bat '''
        if exist jmeter-report rmdir /s /q jmeter-report
        mkdir jmeter-report

        jmeter ^
          -n ^
          -t jmeter\\order_perf_test.jmx ^
          -JHOST=%BACKEND_IP% ^
          -JPORT=5000 ^
          -JFRONTEND_HOST=%FRONTEND_IP% ^
          -JFRONTEND_PORT=80 ^
          -Jjtl=jmeter-report\\results.jtl ^
          -l jmeter-report\\results.jtl ^
          -e -o jmeter-report\\html
        '''
      }
    }

    stage('Validate Orders in Database') {
      steps {
        script {
          def totalOrders = powershell(
            returnStdout: true,
            script: '''
$mysqlPod = kubectl get pods -l app=mysql -o jsonpath="{.items[0].metadata.name}"

Write-Host "Latest order summary:"
kubectl exec $mysqlPod -- mysql -N -B -uretailuser -pRetailPass@123 -D retaildb -e "SELECT id, order_number, customer_name, total_amount, status, created_at FROM orders ORDER BY id DESC LIMIT 10;"

$totalOrders = kubectl exec $mysqlPod -- mysql -N -B -uretailuser -pRetailPass@123 -D retaildb -e "SELECT COUNT(*) FROM orders;"
Write-Output $totalOrders
'''
          ).trim()

          env.TOTAL_ORDERS = totalOrders
          writeFile file: 'db_metrics.txt', text: "TOTAL_ORDERS=${env.TOTAL_ORDERS}\n"

          echo "Total Orders Created: ${env.TOTAL_ORDERS}"
        }
      }
    }

    stage('Extract Performance Metrics') {
      steps {
        powershell '''
$stats = Get-ChildItem -Recurse jmeter-report\\html | Where-Object { $_.Name -eq "statistics.json" }

$data = Get-Content $stats.FullName | ConvertFrom-Json
$total = $data.Total

$users = 50
$tps = [math]::Round($total.throughput, 2)
$error = $total.errorPct
$avg = $total.meanResTime

$metrics = @"
USERS=$users
TPS=$tps
ERROR_RATE=$error
AVG_RESPONSE=$avg
"@

$metrics | Out-File -FilePath metrics.txt -Encoding ascii
'''
      }
    }

    stage('Validate Python & Ollama') {
      steps {
        bat '''
        echo Verifying Python installation
        python --version

        echo Verifying Ollama installation
        ollama --version

        echo Checking installed models
        ollama list
        '''
      }
    }

    stage('Run GenAI Analysis (Ollama)') {
      steps {
        bat '''
        echo Running GenAI performance analysis...
        python genai\\genai_jmeter_pdf_report.py jmeter-report\\html
        '''
      }
    }

    stage('Read AI Analysis Results') {
      steps {
        script {
          def ai = readFile(file: 'jmeter-report/html/ai_summary.txt').trim().split("\\r?\\n")

          env.AI_SCORE = ai.find { it.startsWith("SCORE") }?.split("=")[1]
          env.AI_GRADE = ai.find { it.startsWith("GRADE") }?.split("=")[1]
          env.SLOWEST  = ai.find { it.startsWith("SLOWEST") }?.split("=")[1]

          echo "AI Score: ${env.AI_SCORE}"
          echo "AI Grade: ${env.AI_GRADE}"
          echo "Slowest Endpoint: ${env.SLOWEST}"
        }
      }
    }

    stage('Zip JMeter Report') {
      steps {
        bat '''
        if exist jmeter-report.zip del /f /q jmeter-report.zip
        powershell Compress-Archive ^
          jmeter-report ^
          jmeter-report.zip ^
          -Force
        '''
      }
    }

    stage('Email JMeter Report') {
      steps {
        script {
          def metrics = readFile(file: 'metrics.txt').trim().split("\\r?\\n")

          def USERS = metrics.find { it.startsWith("USERS") }?.split("=")[1]
          def TPS = metrics.find { it.startsWith("TPS") }?.split("=")[1]
          def ERROR = metrics.find { it.startsWith("ERROR_RATE") }?.split("=")[1]
          def AVG = metrics.find { it.startsWith("AVG_RESPONSE") }?.split("=")[1]

          emailext(
            subject: "Retail App + GenAI Performance Report | Build #${BUILD_NUMBER}",
            body: """

Hi Team,

Performance testing completed successfully.

Frontend URL:
http://${FRONTEND_IP}

Backend URL:
http://${BACKEND_IP}:5000

Performance Test Summary
---------------------------------
Concurrent Users           : ${USERS}
Throughput (TPS)           : ${TPS}
Error Rate                 : ${ERROR} %
Avg Response               : ${AVG} ms
Total Orders Created       : ${env.TOTAL_ORDERS}

AI Performance Analysis
---------------------------------
Performance Score          : ${env.AI_SCORE}/100
Performance Grade          : ${env.AI_GRADE}
Slowest Endpoint           : ${env.SLOWEST}

AI Tool Used               : Ollama
Model Used                 : Phi3

Reports Attached:
1. JMeter HTML Dashboard
2. AI Generated Performance PDF Report

Build URL:
${BUILD_URL}

Regards,
Jenkins CI Pipeline
""",
            to: "rithwik10122000@gmail.com",
            attachmentsPattern: "jmeter-report.zip"
          )
        }
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