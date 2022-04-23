podTemplate(containers: [
    containerTemplate(name: 'python-pipelines', image: 'python:3.9.12', ttyEnabled: true, command: 'cat')
  ]) {
      node(POD_LABEL) {
        container('python-pipelines') {
            checkout([
                $class: 'GitSCM',
                branches: [[name: '*/dev']],
                doGenerateSubmoduleConfigurations: false,
                extensions: [],
                submoduleCfg: [],
                userRemoteConfigs: [[url: 'https://github.com/jakub1500/python-pipelines.git']]])
            sh("pip3 install -r requirements.txt")
            params.each{ key, value ->
                echo("${key}=${value}")
                sh("echo ${key}=${value} >> params.txt")
            }
            sh("python3 pipelines")
            if (fileExists('.artifacts')) {
                archiveArtifacts(artifacts: '.artifacts/**')
            }
        }
      }
}