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
    MAVEN_HOME  = "C:\\Maven"
    PATH = "${JAVA_HOME}\\bin;${JMETER_HOME}\\bin;${MAVEN_HOME}\\bin;${env.PATH}"
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
        az provider register --namespace Microsoft.ContainerRegistry

        echo Checking provider registration states...
        az provider show --namespace Microsoft.ContainerService --query "registrationState" -o tsv
        az provider show --namespace Microsoft.Compute --query "registrationState" -o tsv
        az provider show --namespace Microsoft.Network --query "registrationState" -o tsv
        az provider show --namespace Microsoft.Storage --query "registrationState" -o tsv
        az provider show --namespace Microsoft.ContainerRegistry --query "registrationState" -o tsv

        timeout /t 60
        '''
      }
    }

    stage('Wait for ContainerRegistry Provider Registration') {
      steps {
        powershell '''
        $state = ""
        for ($i = 0; $i -lt 20; $i++) {
          $state = az provider show --namespace Microsoft.ContainerRegistry --query "registrationState" -o tsv
          Write-Host "Microsoft.ContainerRegistry state: $state"
          if ($state -eq "Registered") {
            exit 0
          }
          Start-Sleep -Seconds 15
        }
        throw "Microsoft.ContainerRegistry provider is not Registered"
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

    stage('Read Terraform Outputs') {
      steps {
        script {
          env.AKS_NAME = powershell(returnStdout: true, script: '(terraform output -raw aks_name).Trim()').trim()
          env.RESOURCE_GROUP = powershell(returnStdout: true, script: '(terraform output -raw resource_group).Trim()').trim()
          env.ACR_NAME = powershell(returnStdout: true, script: '(terraform output -raw acr_name).Trim()').trim()
          env.ACR_LOGIN_SERVER = powershell(returnStdout: true, script: '(terraform output -raw acr_login_server).Trim()').trim()

          echo "AKS Name        : ${env.AKS_NAME}"
          echo "Resource Group  : ${env.RESOURCE_GROUP}"
          echo "ACR Name        : ${env.ACR_NAME}"
          echo "ACR LoginServer : ${env.ACR_LOGIN_SERVER}"
        }
      }
    }

    stage('Configure Kubernetes Access') {
      steps {
        bat '''
        az aks get-credentials ^
          --resource-group %RESOURCE_GROUP% ^
          --name %AKS_NAME% ^
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

    stage('Verify Docker') {
      steps {
        bat '''
        docker --version
        docker ps
        '''
      }
    }

    stage('Verify Maven') {
      steps {
        bat '''
        mvn -v
        '''
      }
    }

    stage('Build & Push Backend Image to ACR') {
      steps {
        bat '''
        echo Logging in to ACR...
        call az acr login --name %ACR_NAME%

        echo Building backend image...
        docker build -t %ACR_LOGIN_SERVER%/retail-backend:latest backend

        echo Pushing backend image...
        docker push %ACR_LOGIN_SERVER%/retail-backend:latest
        '''
      }
    }

    stage('Verify Backend Image in ACR') {
      steps {
        bat '''
        call az acr repository show-tags --name %ACR_NAME% --repository retail-backend
        '''
      }
    }

    stage('Patch Backend Image in YAML') {
      steps {
        powershell '''
        $filePath = "k8s\\backend-deployment.yaml"
        $content = Get-Content $filePath -Raw
        $replacement = "image: $env:ACR_LOGIN_SERVER/retail-backend:latest"
        $updated = $content -replace 'image:\\s*.*retail-backend:latest', $replacement
        Set-Content -Path $filePath -Value $updated
        Get-Content $filePath
        '''
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
    \$updated = \$content.Replace('__BACKEND_API_URL__', 'http://${env.BACKEND_IP}:5000')
    Set-Content -Path \$filePath -Value \$updated
    Get-Content \$filePath
    """
  }
}

    stage('Build & Push Frontend Image to ACR') {
      steps {
        bat '''
        echo Logging in to ACR...
        call az acr login --name %ACR_NAME%

        echo Building frontend image...
        docker build -t %ACR_LOGIN_SERVER%/retail-frontend:latest frontend

        echo Pushing frontend image...
        docker push %ACR_LOGIN_SERVER%/retail-frontend:latest
        '''
      }
    }

    stage('Verify Frontend Image in ACR') {
      steps {
        bat '''
        call az acr repository show-tags --name %ACR_NAME% --repository retail-frontend
        '''
      }
    }

    stage('Patch Frontend Image in YAML') {
      steps {
        powershell '''
        $filePath = "k8s\\frontend-deployment.yaml"
        $content = Get-Content $filePath -Raw
        $replacement = "image: $env:ACR_LOGIN_SERVER/retail-frontend:latest"
        $updated = $content -replace 'image:\\s*.*retail-frontend:latest', $replacement
        Set-Content -Path $filePath -Value $updated
        Get-Content $filePath
        '''
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
          Expand-Archive $zip C:\\Java -Force
          $extracted = Get-ChildItem C:\\Java | Where-Object { $_.Name -like "jdk-11*" } | Select-Object -First 1
          if ($null -eq $extracted) { throw "JDK extraction failed" }
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
          Expand-Archive jmeter.zip C:\\JMeter -Force
        }
        else {
          Write-Host "JMeter already installed"
        }
        '''
      }
    }

    stage('Run Selenium Functional Tests') {
      steps {
        bat '''
        cd selenium
        mvn test -Dfrontend.url=http://%FRONTEND_IP%
        '''
      }
    }

    stage('Publish Selenium Results') {
      steps {
        junit testResults: 'selenium/target/surefire-reports/*.xml', allowEmptyResults: false
      }
    }

    stage('Extract Functional Metrics') {
      steps {
        powershell '''
        [xml]$xml = Get-Content "selenium\\target\\surefire-reports\\TEST-tests.RetailOrderTest.xml"

        $tests = [int]$xml.testsuite.tests
        $failures = [int]$xml.testsuite.failures
        $errors = [int]$xml.testsuite.errors
        $skipped = [int]$xml.testsuite.skipped
        $passed = $tests - $failures - $errors - $skipped
        $time = $xml.testsuite.time

        $failedNames = @()
        foreach ($tc in $xml.testsuite.testcase) {
          if ($tc.failure -or $tc.error) {
            $failedNames += $tc.name
          }
        }

        $failedText = if ($failedNames.Count -gt 0) { $failedNames -join ", " } else { "None" }

        $metrics = @"
TOTAL_TESTS=$tests
PASSED=$passed
FAILED=$failures
ERRORS=$errors
SKIPPED=$skipped
DURATION=$time
FAILED_TEST_NAMES=$failedText
"@

        $metrics | Out-File -FilePath functional_metrics.txt -Encoding ascii
        Get-Content functional_metrics.txt
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

    stage('Run GenAI Functional Analysis (Ollama)') {
      steps {
        bat '''
        python genai\\genai_selenium_analysis.py functional_metrics.txt
        '''
      }
    }

    stage('Read Functional AI Results') {
      steps {
        script {
          def fai = readFile(file: 'functional_ai_summary.txt').trim().split("\\r?\\n")

          env.FUNC_SCORE = fai.find { it.startsWith("SCORE") }?.split("=", 2)[1]
          env.FUNC_GRADE = fai.find { it.startsWith("GRADE") }?.split("=", 2)[1]
          env.FUNC_ISSUE = fai.find { it.startsWith("TOP_ISSUE") }?.split("=", 2)[1]

          echo "Functional AI Score: ${env.FUNC_SCORE}"
          echo "Functional AI Grade: ${env.FUNC_GRADE}"
          echo "Functional Top Issue: ${env.FUNC_ISSUE}"
        }
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
          powershell '''
$mysqlPod = kubectl get pods -l app=mysql -o jsonpath="{.items[0].metadata.name}"
Write-Host "Latest order summary:"
kubectl exec $mysqlPod -- mysql -N -B -uretailuser -pRetailPass@123 -D retaildb -e "SELECT id, order_number, customer_name, total_amount, status, created_at FROM orders ORDER BY id DESC LIMIT 10;"
'''

          def totalOrders = powershell(
            returnStdout: true,
            script: '''
$mysqlPod = kubectl get pods -l app=mysql -o jsonpath="{.items[0].metadata.name}"
$cnt = kubectl exec $mysqlPod -- mysql -N -B -uretailuser -pRetailPass@123 -D retaildb -e "SELECT COUNT(*) FROM orders;"
Write-Output ($cnt | Select-Object -Last 1)
'''
          ).trim()

          env.TOTAL_ORDERS = totalOrders
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

    stage('Run GenAI Performance Analysis (Ollama)') {
      steps {
        bat '''
        python genai\\genai_jmeter_pdf_report.py jmeter-report\\html
        '''
      }
    }

    stage('Read Performance AI Results') {
      steps {
        script {
          def ai = readFile(file: 'jmeter-report/html/ai_summary.txt').trim().split("\\r?\\n")

          env.AI_SCORE = ai.find { it.startsWith("SCORE") }?.split("=", 2)[1]
          env.AI_GRADE = ai.find { it.startsWith("GRADE") }?.split("=", 2)[1]
          env.SLOWEST  = ai.find { it.startsWith("SLOWEST") }?.split("=", 2)[1]

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

    stage('Email Combined Report') {
  steps {
    script {
      def perf = readFile(file: 'metrics.txt').trim().split("\\r?\\n")
      def func = readFile(file: 'functional_metrics.txt').trim().split("\\r?\\n")

      def USERS = perf.find { it.startsWith("USERS") }?.split("=", 2)[1]
      def TPS = perf.find { it.startsWith("TPS") }?.split("=", 2)[1]
      def ERROR = perf.find { it.startsWith("ERROR_RATE") }?.split("=", 2)[1]
      def AVG = perf.find { it.startsWith("AVG_RESPONSE") }?.split("=", 2)[1]

      def TOTAL_TESTS = func.find { it.startsWith("TOTAL_TESTS") }?.split("=", 2)[1]
      def PASSED = func.find { it.startsWith("PASSED") }?.split("=", 2)[1]
      def FAILED = func.find { it.startsWith("FAILED") }?.split("=", 2)[1]
      def ERRORS = func.find { it.startsWith("ERRORS") }?.split("=", 2)[1]
      def SKIPPED = func.find { it.startsWith("SKIPPED") }?.split("=", 2)[1]
      def DURATION = func.find { it.startsWith("DURATION") }?.split("=", 2)[1]
      def FAILED_TEST_NAMES = func.find { it.startsWith("FAILED_TEST_NAMES") }?.split("=", 2)[1]

      emailext(
        subject: "Retail App Functional + Performance Report | Build #${BUILD_NUMBER}",
        body: """

Hi Team,

Ephemeral testing pipeline completed successfully.

Frontend URL:
http://${FRONTEND_IP}

Backend URL:
http://${BACKEND_IP}:5000

ACR Login Server:
${ACR_LOGIN_SERVER}

Functional Test Summary
---------------------------------
Total Test Cases          : ${TOTAL_TESTS}
Passed                    : ${PASSED}
Failed                    : ${FAILED}
Errors                    : ${ERRORS}
Skipped                   : ${SKIPPED}
Execution Time (sec)      : ${DURATION}
Failed Test Names         : ${FAILED_TEST_NAMES}

AI Functional Analysis
---------------------------------
Functional Score          : ${env.FUNC_SCORE}/100
Functional Grade          : ${env.FUNC_GRADE}
Top Functional Issue      : ${env.FUNC_ISSUE}

Performance Test Summary
---------------------------------
Concurrent Users          : ${USERS}
Throughput (TPS)          : ${TPS}
Error Rate                : ${ERROR} %
Avg Response              : ${AVG} ms
Total Orders Created      : ${env.TOTAL_ORDERS}

AI Performance Analysis
---------------------------------
Performance Score         : ${env.AI_SCORE}/100
Performance Grade         : ${env.AI_GRADE}
Slowest Endpoint          : ${env.SLOWEST}

AI Tool Used              : Ollama
Model Used                : Phi3

Reports Attached:
1. Functional AI Summary TXT
2. Functional AI PDF Report
3. Selenium JUnit XML Report
4. JMeter HTML Dashboard ZIP
5. AI Performance PDF Report

Build URL:
${BUILD_URL}

Regards,
Jenkins CI Pipeline
""",
        to: "rithwik10122000@gmail.com",
        attachmentsPattern: "functional_ai_summary.txt, Functional_AI_Report.pdf, selenium/target/surefire-reports/*.xml, jmeter-report.zip, jmeter-report/html/AI_Performance_Report.pdf"
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