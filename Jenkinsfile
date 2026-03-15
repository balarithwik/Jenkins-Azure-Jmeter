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
    script {
      def ip = powershell(
        returnStdout: true,
        script: '''


$ip = ""
for ($i = 0; $i -lt 40; $i++) {
try {
$svc = kubectl get svc nginx -o json | ConvertFrom-Json
$ip = $svc.status.loadBalancer.ingress[0].ip
if ($ip) {
Write-Output $ip
exit 0
}
} catch {
Write-Host "Waiting for LoadBalancer IP..."
}
Start-Sleep -Seconds 10
}
throw "Failed to get NGINX LoadBalancer IP"
'''
).trim()


      env.APP_IP = ip
      echo "Application URL: http://${env.APP_IP}"
    }
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

Invoke-WebRequest `    -Uri https://downloads.apache.org/jmeter/binaries/apache-jmeter-5.6.3.zip`
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

stage('Wait for NGINX Deployment') {
  steps {
    bat '''
    kubectl rollout status deployment/nginx --timeout=300s
    kubectl get pods -l app=nginx
    kubectl get endpoints nginx
    '''
  }
}

stage('Validate Application Endpoints') {
  steps {
    bat """
    echo Validating Home Page
    curl -f http://${APP_IP}/index.html || exit 1

    echo Validating About Page
    curl -f http://${APP_IP}/about.html || exit 1

    echo Validating Contact Page
    curl -f http://${APP_IP}/contact.html || exit 1
    """
  }
}

stage('Run JMeter Test (Native)') {
  steps {
    bat '''
    if exist jmeter-report rmdir /s /q jmeter-report
    mkdir jmeter-report

    jmeter ^
      -n ^
      -t jmeter\\web_perf_test.jmx ^
      -JHOST=%APP_IP% ^
      -JPORT=80 ^
      -Jjtl=jmeter-report\\results.jtl ^
      -l jmeter-report\\results.jtl ^
      -e -o jmeter-report\\html
    '''
  }
}

stage('Extract Performance Metrics') {
  steps {
    powershell '''
$stats = Get-ChildItem -Recurse jmeter-report\\html | Where-Object { $_.Name -eq "statistics.json" }

$data = Get-Content $stats.FullName | ConvertFrom-Json
$total = $data.Total

$users = 50
$tps = [math]::Round($total.throughput,2)
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

stage('Zip JMeter Report') {
  steps {
    bat '''
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
        subject: "JMeter + GenAI Performance Report | Build #${BUILD_NUMBER}",
        body: """


Hi Team,

Performance testing completed successfully.

Application URL:
http://${APP_IP}

## Performance Test Summary

Concurrent Users : ${USERS}
Throughput (TPS) : ${TPS}
Error Rate       : ${ERROR} %
Avg Response     : ${AVG} ms

## GenAI Analysis

AI Tool Used : Ollama (Local LLM)
Model Used   : Phi3

Reports Attached:

1. JMeter HTML Dashboard
2. AI Generated Performance PDF Report
3. Raw JMeter Results

Build URL:
${BUILD_URL}

Environment:
Ephemeral AKS Performance Test Environment

Regards,
Jenkins CI Pipeline
""",
to: "[rithwik10122000@gmail.com](mailto:rithwik10122000@gmail.com)",
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
