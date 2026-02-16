pipeline {
  agent any

  environment {
    ARM_CLIENT_ID       = credentials('ARM_CLIENT_ID')
    ARM_CLIENT_SECRET   = credentials('ARM_CLIENT_SECRET')
    ARM_SUBSCRIPTION_ID = credentials('ARM_SUBSCRIPTION_ID')
    ARM_TENANT_ID       = credentials('ARM_TENANT_ID')

    TF_IN_AUTOMATION = "true"
  }

  stages {

    stage('Checkout Code') {
      steps {
        git branch: 'main',
            url: 'https://github.com/balarithwik/Jenkins-Azure-Jmeter.git'
      }
    }
stage('Register Azure Resource Providers') {
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

    echo Waiting for provider registration...
    timeout /t 30
    '''
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

    stage('Configure Kubernetes Access') {
      steps {
        bat '''
        az login --service-principal ^
          -u %ARM_CLIENT_ID% ^
          -p %ARM_CLIENT_SECRET% ^
          --tenant %ARM_TENANT_ID%

        az account set --subscription %ARM_SUBSCRIPTION_ID%

        az aks get-credentials ^
          --resource-group demo-rg ^
          --name demo-aks ^
          --overwrite-existing
        '''
      }
    }

    stage('Wait for Kubernetes Ready') {
      steps {
        bat 'kubectl wait --for=condition=Ready nodes --all --timeout=300s'
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
          env.APP_IP = bat(
            script: '''
            for /L %%i in (1,1,30) do (
              kubectl get svc nginx ^
                -o jsonpath="{.status.loadBalancer.ingress[0].ip}" && exit /b 0
              timeout /t 10 >nul
            )
            ''',
            returnStdout: true
          ).trim()
        }

        bat '''
        if "%APP_IP%"=="" (
          echo Failed to fetch LoadBalancer IP
          exit /b 1
        )
        '''

        echo "Application URL: http://${APP_IP}"
      }
    }

    stage('Run JMeter Test (Docker)') {
      steps {
        bat '''
        docker run --rm ^
          -v %CD%/jmeter:/jmeter ^
          -v %CD%/jmeter-report:/report ^
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