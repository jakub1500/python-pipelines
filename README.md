# Python Pipelines
```
             _   _                         _            _ _                 
 _ __  _   _| |_| |__   ___  _ __    _ __ (_)_ __   ___| (_)_ __   ___  ___ 
| '_ \| | | | __| '_ \ / _ \| '_ \  | '_ \| | '_ \ / _ \ | | '_ \ / _ \/ __|
| |_) | |_| | |_| | | | (_) | | | | | |_) | | |_) |  __/ | | | | |  __/\__ \
| .__/ \__, |\__|_| |_|\___/|_| |_| | .__/|_| .__/ \___|_|_|_| |_|\___||___/
|_|    |___/                        |_|     |_|                            
```
This script is inteded to be an alternative to Jenkins pipelines. \
The main purpose is to be able to use Kubernetes features from within Python code (because everybody hates groovy).

Main mode for script is to run it from already created pod by Jenkins (pod needs to have python3 installed).

For local run purpose `relocation` option was added. Long story short - after executing the script it will create \
Python 3 supporting pod where it will copy itself, then it will execute itself from newly created pod. \
This behavior should imitate environment like it was executed from pod running in jenkins world.

There is option to disable `relocation` while running in local environment. This can be achieved by \
adding flag `--no-relocate`.

# Preparation
1) Make sure you have correct permissions in cluster that your kube config is pointing. \
   Permissions needed can be found in `additional_source/rbac-permissions.yaml`.
2) To prepare cluster in pre-defined namespaces simply execute `setup` script which will create all needed \
   roles and service accounts in `python-pipelines` and `python-pipelines-test` namespaces.
    ```
    $ ./setup
    ```
3) Install pip packages
    ```
    $ pip3 install -r requirements.txt
    ```
# Execute pipelines
    $ python3 ./pipelines
