from kubernetes import client
from kubernetes.stream import stream
from kubernetes.stream.ws_client import WSClient
from utils.common import generate_random_string, PipelinesException
from utils.logger import Logger
from utils.environment import env
import os
import base64
import yaml
import tarfile
import io

pod_templates = None
with open(f"{os.path.dirname(os.path.realpath(__file__))}/pod_config.yaml", 'r') as config:
    pod_templates = yaml.safe_load(config)

def get_pod_details(pod_template_name: str):
    pod_details: dict = pod_templates[pod_template_name]
    if "restart_policy" not in pod_details:
        pod_details["restart_policy"] = "Never"
    if "image_pull_policy" not in pod_details:
        pod_details["image_pull_policy"] = "IfNotPresent"
    if "namespace" not in pod_details:
        pod_details["namespace"] = env["kubernetes"]["default_namespace"]
    return pod_details

class Pod:
    labels: dict = {
        "python-pipelines": "True"
    }

    def __init__(self, pod_template_name: str, name: str = None, pod_timeout: int = 3600):
        pod_details = get_pod_details(pod_template_name)
        self.image: str = pod_details["image"]
        self.name: str = f'{pod_template_name}-{generate_random_string(10)}'
        self.namespace: str = pod_details["namespace"]
        self.serviceaccount: str = env["kubernetes"]["default_serviceaccount"]
        self.restart_policy: str = pod_details["restart_policy"]
        self.image_pull_policy: str = pod_details["image_pull_policy"]
        self.resources: dict = pod_details["resources"] if "resources" in pod_details else {}
        self.pod_timeout: int = pod_timeout
        self.api_instance: client.CoreV1Api = env["kubernetes"]["api"]
        self._pod: client.V1Pod = client.V1Pod()
        self._prepare_kubernetes_pod()

    def __enter__(self):
        self.spawn()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.delete()

    def _prepare_kubernetes_pod(self) -> None:
        self._pod.metadata = client.V1ObjectMeta(name=self.name, labels=self.labels)
        if self.resources:
            resource_requirements: client.V1ResourceRequirements = client.V1ResourceRequirements(limits=self.resources["limits"], requests=self.resources["requests"])
            container = client.V1Container(name=self.name, image=self.image, image_pull_policy=self.image_pull_policy, resources=resource_requirements)
        else:
            container = client.V1Container(name=self.name, image=self.image, image_pull_policy=self.image_pull_policy)
        container.args = ["sleep", f"{self.pod_timeout}"]
        spec = client.V1PodSpec(containers=[container], restart_policy=self.restart_policy, service_account_name=self.serviceaccount)
        self._pod.spec = spec

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
            time.sleep(0.1)

    def spawn(self):
        self.api_instance.create_namespaced_pod(namespace=self.namespace, body=self._pod, async_req=False)
        env["kubernetes"]["pods"].append(self.name)
        self.wait_for_running_status()

        Logger.info(f"{self.name} spawned.")
        self.print_pod_details()


    def delete(self):
        self.api_instance.delete_namespaced_pod(self.name, self.namespace)
        env["kubernetes"]["pods"].remove(self.name)
        Logger.info(f"{self.name} deleted")

    def exec(self, command: str, silent: bool = False, useLegacyShell: bool = False, maxOutputCharacters: int = 10000) -> dict:
        def _append_output(content):
            nonlocal output
            nonlocal lock_output_buffer
            if len(output) + len(content) > maxOutputCharacters:
                lock_output_buffer = True
            if not lock_output_buffer:
                output = output + content

        self.wait_for_running_status()
        lock_output_buffer = False
        output = ""
        final_command = ["sh" if useLegacyShell else "bash", "-c", command]
        resp: WSClient = stream(self.api_instance.connect_get_namespaced_pod_exec,
                    self.name,
                    self.namespace,
                    command=final_command,
                    stderr=True, stdin=False,
                    stdout=True, tty=False, _preload_content=False)

        while resp.is_open():
            resp.update(timeout=1)
            if resp.peek_stdout():
                content = resp.read_stdout().strip()
                if not silent:
                    Logger.info(content)
                _append_output(content)
            if resp.peek_stderr():
                content = resp.read_stderr().strip()
                if not silent:
                    Logger.info(content)
                _append_output(content)

        resp.close()
        return {"ret_val": resp.returncode, "output": output}

    def copy_file_from(self, source: str, destination: str) -> None:
        """
        This method provides an interface to copy file or whole dirs from pod
        to host filesystem (typically where pipelines script is running).
        `destination` parameter points to directory where the copied files
        will be written, so if we want to copy /etc directory from pod to
        local path /tmp/localpath the destination paramter needs to contain that path.
        """
        temp_file: str = self.create_temp_file()
        self.exec(f'cd $(dirname {source}) && tar -czvf {temp_file} $(basename {source})', silent=True, useLegacyShell=True)

        resp: WSClient = stream(self.api_instance.connect_get_namespaced_pod_exec,
                    self.name,
                    self.namespace,
                    command=["sh", "-c" ,f"base64 {temp_file}"],
                    stderr=True, stdin=False,
                    stdout=True, tty=False)
        tar_content = base64.b64decode(resp)
        io_bytes = io.BytesIO(tar_content)
        tar = tarfile.open(fileobj=io_bytes, mode='r')
        tar.extractall(path=destination)
        tar.close()
        self.exec(f'rm {temp_file}', silent=True, useLegacyShell=True)

    def copy_file_to(self, source: str, destination: str) -> None:
        in_memory_tar = io.BytesIO()
        with tarfile.open(fileobj=in_memory_tar, mode='w:gz') as tar:
            tar.add(source, arcname=os.path.basename(source))

        temp_file: str = self.create_temp_file()

        resp: WSClient = stream(self.api_instance.connect_get_namespaced_pod_exec, self.name, self.namespace,
                    command=["sh"],
                    stderr=True, stdin=True,
                    stdout=True, tty=False,
                    _preload_content=False)

        commands = []
        commands.append(f"cat <<'EOF' > {temp_file}\n")
        commands.append(base64.b64encode(in_memory_tar.getvalue()) + b'\n')
        commands.append("EOF\n")

        while resp.is_open():
            resp.update(timeout=1)
            if commands:
                c = commands.pop(0)
                resp.write_stdin(c)
            else:
                break
        resp.close()

        self.exec(f"mkdir -p {destination}", silent=True, useLegacyShell=True)
        self.exec(f"base64 -d {temp_file} | tar zxf - --directory {destination}", silent=True, useLegacyShell=True)
        self.exec(f"rm -f {temp_file}", silent=True, useLegacyShell=True)

    def archive_artifact(self, path) -> None:
        """
        This method is responsible for copying pointed artifact to configured artifacts directory
        inside of main pipelines pod. Path given as argument will accept files and dirs. In case if
        path to dir is passed, whole dir will be archived. It is worth to note that if artifact of
        same name has been already archived it will be overrided.
        """
        artifacts_dir_path: str = env["general"]["artifacts_path"]

        if not self.check_exists(path):
            raise ArtifactNotExistsException(
                f"Attempted to create an artifact from {path} in {self.name} ({self.image}) which doesn't exist")
        if not os.path.exists(artifacts_dir_path):
            os.mkdir(artifacts_dir_path)

        self.copy_file_from(path, artifacts_dir_path)

    def print_pod_details(self) -> None:
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

    def check_is_file(self, path: str) -> bool:
        return self.exec(f"test -f {path}", silent=True, useLegacyShell=True)["ret_val"] == 0

    def check_exists(self, path: str) -> bool:
        return self.exec(f"test -e {path}", silent=True, useLegacyShell=True)["ret_val"] == 0

    def check_is_dir(self, path: str) -> bool:
        return self.exec(f"test -d {path}", silent=True, useLegacyShell=True)["ret_val"] == 0

    def create_temp_file(self) -> str:
        return self.exec("mktemp", silent=True, useLegacyShell=True)["output"]


class PodException(PipelinesException):
    pass


class ArtifactNotExistsException(PodException):
    pass