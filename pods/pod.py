from kubernetes import client
from kubernetes.stream import stream
from kubernetes.stream.ws_client import ERROR_CHANNEL
from utils.common import generate_random_string
from utils.logger import Logger
from utils.environment import env
import os
import base64
import json
import yaml

pod_templates = None
with open(f"{os.path.dirname(os.path.realpath(__file__))}/pod_config.yaml", 'r') as config:
    pod_templates=yaml.safe_load(config)

def get_pod_details(pod_template_name):
    pod_details = pod_templates[pod_template_name]
    if "restart_policy" not in pod_details:
        pod_details["restart_policy"] = "Never"
    if "image_pull_policy" not in pod_details:
        pod_details["image_pull_policy"] = "IfNotPresent"
    if "namespace" not in pod_details:
        pod_details["namespace"] = env["kubernetes"]["default_namespace"]
    return pod_details

class Pod:
    labels = {
        "python-pipelines": "True"
    }

    def __init__(self, pod_template_name, name=None, pod_timeout=3600):
        pod_details = get_pod_details(pod_template_name)
        self.image: str = pod_details["image"]
        self.name: str = f'{pod_template_name}-{generate_random_string(10)}'
        self.namespace = pod_details["namespace"]
        self.restart_policy: str = pod_details["restart_policy"]
        self.image_pull_policy: str = pod_details["image_pull_policy"]
        self.resources = pod_details["resources"] if "resources" in pod_details else None
        self.pod_timeout: int = pod_timeout
        self.api_instance : client.CoreV1Api = env["kubernetes"]["api"]
        self._prepare_kubernetes_pod()

    def __enter__(self):
        self.spawn()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete()

    def _prepare_kubernetes_pod(self):
        self.pod = client.V1Pod()
        self.pod.metadata = client.V1ObjectMeta(name=self.name, labels=self.labels)
        if self.resources:
            resource_requirements: client.V1ResourceRequirements = client.V1ResourceRequirements(limits=self.resources["limits"], requests=self.resources["requests"])
            container = client.V1Container(name=self.name, image=self.image, image_pull_policy=self.image_pull_policy, resources=resource_requirements)
        else:
            container = client.V1Container(name=self.name, image=self.image, image_pull_policy=self.image_pull_policy)
        container.args = ["sleep", f"{self.pod_timeout}"]
        spec = client.V1PodSpec(containers=[container], restart_policy=self.restart_policy)
        self.pod.spec = spec

    @property
    def is_running(self):
        """
        Possible statuses available in V1PodStatus.phase are:
        ["Failed", "Pending", "Running", "Succeeded", "Unknown"]
        """
        pod_details: client.V1Pod = self.api_instance.read_namespaced_pod_status(self.name, self.namespace, async_req=False)
        pod_status: client.V1PodStatus = pod_details.status
        pod_phase: str = pod_status.phase
        return pod_phase == "Running"

    def wait_for_running_status(self):
        while not self.is_running:
            import time
            time.sleep(0.5)

    def spawn(self):
        self.api_instance.create_namespaced_pod(namespace=self.namespace, body=self.pod, async_req=False)
        env["kubernetes"]["pods"].append(self.name)
        self.wait_for_running_status()

        Logger.info(f"{self.name} spawned.")
        self.print_pod_details()


    def delete(self):
        self.api_instance.delete_namespaced_pod(self.name, self.namespace)
        Logger.info(f"{self.name} deleted")

    def exec(self, command, silent=False, useLegacyShell=False) -> int:
        self.wait_for_running_status()
        final_command = ["sh" if useLegacyShell else "bash", "-c", command]
        resp = stream(self.api_instance.connect_get_namespaced_pod_exec,
                    self.name,
                    self.namespace,
                    command=final_command,
                    stderr=True, stdin=False,
                    stdout=True, tty=False, _preload_content=False)
 
        while resp.is_open():
            if resp.peek_stdout() and not silent:
                content = resp.read_stdout()
                Logger.info(content.strip())
            if resp.peek_stderr():
                content = resp.read_stderr()
                Logger.info(content.strip())

        return self._get_error_code_from_stream_response(resp)

    def copy_file(self, source, destination):
        exec_command = ["sh"]
        resp = stream(self.api_instance.connect_get_namespaced_pod_exec, self.name, self.namespace,
                    command=exec_command,
                    stderr=True, stdin=True,
                    stdout=True, tty=False,
                    _preload_content=False)

        file = open(source, "rb")

        commands = []
        commands.append("cat <<'EOF' >" + f'{destination}.base64' + "\n")
        commands.append(base64.b64encode(file.read()) + b'\n')
        commands.append("EOF\n")

        while resp.is_open():
            resp.update(timeout=1)
            if commands:
                c = commands.pop(0)
                resp.write_stdin(c)
            else:
                break

        resp.close()

        self.exec(f"base64 -d {destination}.base64 > {destination}")
        self.exec(f"rm -f {destination}.base64")

    def copy_directory(self, source, destination):
        def _copy_directory(source, destination):
            for name in os.listdir(source):
                if os.path.isfile(f'{source}/{name}'):
                    self.copy_file(f"{source}/{name}", f"{destination}/{name}")
                else:
                    self.exec(f"mkdir -p {destination}/{name}")
                    _copy_directory(f"{source}/{name}", f"{destination}/{name}")
        
        self.exec(f"mkdir -p {destination}")
        _copy_directory(source, destination)

    def print_pod_details(self):
        resources_details = ""
        if self.resources:
            resources_details = f"  resources:\n" + \
                                f"    limits:\n" + \
                                f"      memory:{self.resources['limits']['memory']}\n" + \
                                f"      cpu:{self.resources['limits']['cpu']}\n" + \
                                f"    requests:\n" + \
                                f"      memory:{self.resources['requests']['memory']}\n" + \
                                f"      cpu:{self.resources['requests']['cpu']}\n"
        Logger.info(f"\n{self.name} details:\n" +
                    f"  image: {self.image}\n" +
                    f"  namespace: {self.namespace}\n" +
                    f"{'' if not resources_details else resources_details}")

    def _get_error_code_from_stream_response(self, resp) -> int:
        """
        This function returns integer return code from Kubernetes stream 
        To retrieve Error code from executed command we need to read
        ERROR_CHANNEL message.
        * On success it looks like:
            {"metadata":{},"status":"Success"}
        * On failure:
            {"metadata":{},"status":"Failure"
            "message":"command terminated with non-zero exit code: Error executing in Docker Container: 5",
            "reason":"NonZeroExitCode","details":{"causes":[{"reason":"ExitCode","message":"5"}]}}
        """
        err: str = resp.read_channel(ERROR_CHANNEL)
        json_err: json = json.loads(err)
        if json_err["status"] == "Success":
            return 0
        else:
            return int(json_err["details"]["causes"][0]["message"])
