import unittest
import time
import tempfile
import os
from utils.environment import env
from utils.common import exec
from k8s.pod import Pod
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from tests.integration_tests.generic_test import GenericTest



class PodTests(GenericTest):

    def get_running_pods(self) -> list:
        ret = self.kubernetes_api.list_namespaced_pod(namespace=env["kubernetes"]["default_namespace"])
        return [name.metadata.name for name in ret.items]

    def get_status_of_pod(self, name, namespace="test") -> str:
        pod_details: client.V1Pod = self.kubernetes_api.read_namespaced_pod_status(name, namespace, async_req=False)
        pod_status: client.V1PodStatus = pod_details.status
        pod_phase: str = pod_status.phase
        return pod_phase == "Running"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Workaround for issue with kubernetes api connection not closed which prints:
        # `ResourceWarning: unclosed <ssl.SSLSocket...`
        # https://github.com/kubernetes-client/python/issues/309
        import warnings
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*<ssl.SSLSocket.*>")
    

    def test_create_pod(self):
        """
        Test to confirm that pods can be created and deleted.
        Currently there is no possibilities to check if pod is in `terminating` phase,
        so read status of pod needs to be used. Once it will throw exception with reason
        `Not Found` we can be sure it doesn't exist anymore.
        Seems like the timeout of ~180 seconds for pod deletion is reasonable.
        """
        spawned_pod_name = None
        with Pod("busybox") as pod:
            spawned_pod_name = pod.name
            self.assertTrue(spawned_pod_name in self.get_running_pods(), "Proper pod wasn't spawned")
        timeout = 180
        while timeout > 0:
            timeout = timeout - 1
            try:
                self.get_status_of_pod(spawned_pod_name)
                time.sleep(1)
                continue
            except ApiException as e:
                if e.reason == "Not Found":
                    return
        self.fail("Previously spawned pod wasn't deleted!")

    def test_copy_from_pod(self):
        """
        Test to verify is coping files and dirs from pod works correctly.
        """
        with Pod("busybox") as pod:
            with tempfile.TemporaryDirectory() as tmpdirname:
                pod.copy_file_from("/etc", tmpdirname)
                self.assertTrue(os.path.exists(f'{tmpdirname}/etc'), "/etc directory not copied properly from pod.")
                self.assertTrue(os.path.isdir(f'{tmpdirname}/etc'), "Copied /etc directory is not a dir.")
                self.assertTrue(os.path.exists(f'{tmpdirname}/etc/passwd'), "/etc/passwd file not copied properly from pod.")
                self.assertTrue(os.path.isfile(f'{tmpdirname}/etc/passwd'), "Copied /etc/passwd file is not a file.")
            with tempfile.TemporaryDirectory() as tmpdirname:
                pod.copy_file_from("/etc/passwd", tmpdirname)
                self.assertTrue(os.path.exists(f'{tmpdirname}/passwd'), "/etc/passwd file not copied properly from pod.")
                self.assertTrue(os.path.isfile(f'{tmpdirname}/passwd'), "Copied /etc/passwd file is not a file.")

if __name__=='__main__':
    unittest.main()