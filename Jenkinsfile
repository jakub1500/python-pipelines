import groovy.json.JsonOutput 

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

            String params_string = ''
            if (!params.isEmpty()) {
                String params_json_string = JsonOutput.toJson(params).replace("\"", "\\\"")
                params_string = "-p \"${params_json_string}\""
            }

            echo(params_string)
            sh("python3 pipelines -j ${JOB_NAME} ${params_string}")
            if (fileExists('.artifacts')) {
                archiveArtifacts(artifacts: '.artifacts/**')
            }
        }
      }
}