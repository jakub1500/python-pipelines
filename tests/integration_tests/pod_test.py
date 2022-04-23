from re import I
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
                time.sleep(0.3)
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

    def test_exec_pod_correct_return_value(self):
        """
        Test to verifyif exec command on pod returns correct return value.
        """
        with Pod("busybox") as pod:
            ret_val = pod.exec("ls /etc/passwd", silent=True, useLegacyShell=True)["ret_val"]
            self.assertEqual(ret_val, 0, f"Executed command shoud return value 0, but returned {ret_val}")

            ret_val = pod.exec("ls /etc/passwddddddddd", silent=True, useLegacyShell=True)["ret_val"]
            self.assertNotEqual(ret_val, 0, f"Executed command shoud return value !=0, but returned {ret_val}")

    def test_exec_pod_correct_output(self):
        """
        Test to verif yif exec command on pod returns correct output.
        """
        with Pod("busybox") as pod:
            output = pod.exec("cat /etc/hostname", useLegacyShell=True)["output"]
            self.assertEqual(output, pod.name, f"Executed command output hostname, but outputed {output}")

    def test_exec_pod_correct_output_limited(self):
        """
        Test to verify if exec command on pod returns correct limited in character output.
        """
        content = "1234567890"
        with Pod("busybox") as pod:
            for i in range(1,4):
                approximate_output_length = i * 10 * len(content)
                limit = approximate_output_length - 5
                output = pod.exec(f"for i in $(seq 1 {i*10}); do echo {content}; done", silent=True, useLegacyShell=True, maxOutputCharacters=limit)["output"]
                self.assertTrue(len(output) <= limit, f"Output limit was set to {limit}, but output had {len(output)} characters.")

    def test_copy_to_pod(self):
        """
        Test to verify if coping files and dirs to pod works correctly.
        """
        with Pod("busybox") as pod:
            test_content = "somecontent"
            test_file_name = "somefile"
            destination_dir = "/optopt"
            with tempfile.TemporaryDirectory() as tmpdirname:
                with open(f'{tmpdirname}/{test_file_name}', "wb") as f:
                    f.write(bytes(test_content, 'utf-8'))

                pod.copy_file_to(f'{tmpdirname}/{test_file_name}', destination_dir)
                self.assertTrue(pod.check_exists(f"{destination_dir}/{test_file_name}"), "File wasn't created in pod.")
                self.assertTrue(pod.check_is_file(f"{destination_dir}/{test_file_name}"), "File created in pod is not a file.")
                pod_file_content = pod.exec(f"cat {destination_dir}/{test_file_name}", silent=True, useLegacyShell=True)["output"]
                self.assertEqual(pod_file_content, test_content, f"Content of copied file is different.")

            with tempfile.TemporaryDirectory() as tmpdirname:
                for i in range(2):
                    with open(f'{tmpdirname}/{test_file_name}.{i}', "wb") as f:
                        f.write(bytes(f"{test_content}{i}", "utf-8"))

                tmpDirOnlyName = tmpdirname.split("/")[-1]

                pod.copy_file_to(f'{tmpdirname}', destination_dir)
                self.assertTrue(pod.check_exists(f"{destination_dir}/{tmpDirOnlyName}"), "Dir wasn't created in pod.")
                self.assertTrue(pod.check_is_dir(f"{destination_dir}/{tmpDirOnlyName}"), "Dir created in pod is not a dir.")

                for i in range(2):
                    test_file_path = f"{destination_dir}/{tmpDirOnlyName}/{test_file_name}.{i}"
                    test_file_content = f"{test_content}{i}"
                    self.assertTrue(pod.check_exists(f"{test_file_path}"), "File wasn't created in pod.")
                    self.assertTrue(pod.check_is_file(f"{test_file_path}"), "File created in pod is not a file.")
                    pod_file_content = pod.exec(f"cat {test_file_path}", silent=True, useLegacyShell=True)["output"]
                    self.assertEqual(pod_file_content, f"{test_file_content}", f"Content of copied file is different.")

    def test_archive_artifact_files(self):
        """
        Test to verify if archiving of files artifacts works correctly.
        """
        test_content = "marchewka"
        test_file_name = "kalafior"
        test_file_dir = "/tmp"
        test_file_path = os.path.join(test_file_dir, test_file_name)

        for i in range(2):
            with Pod("busybox") as pod:
                pod.exec(f"echo -n {test_content}{i} > {test_file_path}{i}", silent=True, useLegacyShell=True)
                pod.archive_artifact(f"{test_file_path}{i}")
        
        for i in range(2):
            final_artifact_path = os.path.join(env["general"]["artifacts_path"], f"{test_file_name}{i}")
            self.assertTrue(os.path.exists(final_artifact_path), "Artifact wasn't created.")
            self.assertTrue(os.path.isfile(final_artifact_path), "Archived artifacts is not a file")
            with open(final_artifact_path, "r") as f:
                read_content = f.read()
                self.assertEqual(f"{test_content}{i}", read_content, "Test content differs from the read one.")

    def test_archive_artifact_dirs(self):
        """
        Test to verify if archiving of dirs artifacts works correctly.
        """
        test_content = "marchewka"
        test_file_name = "kalafior"
        test_dir_generic = "brokul"
        test_file_path_generic = os.path.join("/tmp", test_dir_generic)

        for i in range(2):
            with Pod("busybox") as pod:
                test_dir_path = f"{test_file_path_generic}{i}"
                test_file_path = os.path.join(test_dir_path, test_file_name)
                pod.exec(f"mkdir -p {test_dir_path}", silent=True, useLegacyShell=True)
                pod.exec(f"echo -n {test_content} > {test_file_path}", silent=True, useLegacyShell=True)
                pod.archive_artifact(f"{test_dir_path}")
        
        for i in range(2):
            test_dir_path = f"{test_file_path_generic}{i}"
            test_file_path = os.path.join(test_dir_path, test_file_name)
            final_artifact_path = os.path.join(env["general"]["artifacts_path"], f"{test_dir_generic}{i}")
            final_artifact_inside_dir_path = os.path.join(final_artifact_path, test_file_name)
            self.assertTrue(os.path.exists(final_artifact_path), "Artifact wasn't created")
            self.assertTrue(os.path.isdir(final_artifact_path), "Archived artifact is not a dir")
            self.assertTrue(os.path.isfile(final_artifact_inside_dir_path), "Archived artifact insidr dir is not a file")
            with open(final_artifact_inside_dir_path, "r") as f:
                read_content = f.read()
                self.assertEqual(f"{test_content}", read_content, "Test content differs from the read one.")

if __name__=='__main__':
    unittest.main()