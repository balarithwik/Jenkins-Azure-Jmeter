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

    stage('Terraform Init') {
      steps {
        bat 'terraform init'
      }
    }

    stage('Terraform Plan') {
      steps {
        bat 'terraform plan'
      }
    }

    stage('Terraform Apply') {
      steps {
        bat 'terraform apply -auto-approve'
      }
    }

    stage('Provision & Run JMeter') {
      steps {
        echo 'Install Java, JMeter, create HTML pages, run JMeter test'
        // your SSH / remote-exec / scripts here
      }
    }

    stage('Email JMeter Report') {
      steps {
        echo 'Send JMeter HTML report via email'
        // emailext step
      }
    }
  }

  post {

    always {
      echo '⚠️ Cleaning up infrastructure (terraform destroy will ALWAYS run)'
      bat 'terraform destroy -auto-approve'
    }

    success {
      echo '✅ Pipeline completed successfully'
    }

    failure {
      echo '❌ Pipeline failed, but infrastructure was destroyed'
    }
  }
}