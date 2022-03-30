# Python Pipelines
```
             _   _                         _            _ _                 
 _ __  _   _| |_| |__   ___  _ __    _ __ (_)_ __   ___| (_)_ __   ___  ___ 
| '_ \| | | | __| '_ \ / _ \| '_ \  | '_ \| | '_ \ / _ \ | | '_ \ / _ \/ __|
| |_) | |_| | |_| | | | (_) | | | | | |_) | | |_) |  __/ | | | | |  __/\__ \
| .__/ \__, |\__|_| |_|\___/|_| |_| | .__/|_| .__/ \___|_|_|_| |_|\___||___/
|_|    |___/                        |_|     |_|                            
```
This script is inteded to be an alternative to Jenkins pipelines.
The main purpose is to be able to use Kubernetes features from within Python code (because everybody hates groovy).

Main mode for script is to run it from already created pod by Jenkins (pod needs to have python3 installed).

For local run purpose `relocation` option was added. Long story short - after executing the script it will create \
Python 3 supporting pod where it will copy itself, then it will execute itself in newly created pod. \
This behavior should imitate environment like it was executed from pod running in jenkins world. \
To enable this mode simply add `--local-run` as main script argument.

There is option to disable `relocation` while running in local environment. This can be achieved by \
adding flags `--local-run` and `--no-relocate`.

# Preparation
1) Make sure you have correct permissions in cluster that your kube config is pointing.
   Permissions needed:
   * pod write access
   * secret write access (for tests) read access (for pipelines)
2) For relocation mode and for running directly from Jenkins make sure `serviceaccount` used by main pod has access to kube api. \
   In case it hasn't feel free to use yaml below to add `edit` permissions in `test` namespace for `default` `serviceaccount` in `test` namespace
    ```
    apiVersion: rbac.authorization.k8s.io/v1
    kind: RoleBinding
    metadata:
      name: test
      namespace: test
    roleRef:
      apiGroup: rbac.authorization.k8s.io
      kind: ClusterRole
      name: edit
    subjects:
    - kind: ServiceAccount
      name: default
      namespace: test
    ```
3) Install pip packages
    ```
    $ pip3 install -r requirements.txt
    ```
# Execute pipelines
   * locally
  
    $ python3 ./pipelines --local-run

   * directly in Jenkins
  
    $ python3 ./pipelines
