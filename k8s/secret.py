from utils.environment import env
from utils.logger import Logger
from utils.common import decode_base64_to_str
from kubernetes import client
from kubernetes.client.models import v1_secret
import base64
from abc import ABC, abstractmethod

class Secret(ABC):

    @abstractmethod
    def __init__(self, name: str, namespace: str=None):
        if namespace is None:
            namespace = env["kubernetes"]["default_namespace"]
        self.api_instance : client.CoreV1Api = env["kubernetes"]["api"]
        self.k8s_secret : v1_secret.V1Secret = self.api_instance.read_namespaced_secret(name, namespace)
        self._data : dict = self.k8s_secret.data
        for value in self._data.values():
            decoded_value = decode_base64_to_str(value)
            if decoded_value not in env["general"]["secrets"]:
                env["general"]["secrets"].append(decoded_value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.remove_secrets_from_env()

    def remove_secrets_from_env(self):
        for value in self._data.values():
            value_decoded = decode_base64_to_str(value)
            if value_decoded in env["general"]["secrets"]:
                env["general"]["secrets"].remove(value_decoded)

class SecretUserPassword(Secret):
    
    def __init__(self, name: str, namespace: str=None):
        super().__init__(name, namespace)
        self.username = decode_base64_to_str(self._data["username"])
        self.password = decode_base64_to_str(self._data["password"])
