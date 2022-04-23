import unittest
import tempfile
import shutil
from utils.environment import env
from kubernetes import client, config


class GenericTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("Setting up the environmet")
        config.load_kube_config()
        env["kubernetes"] = {}
        env["kubernetes"]["api"] = client.CoreV1Api()
        env["kubernetes"]["pods"] = []
        env["kubernetes"]["default_namespace"] = "python-pipelines-test"
        env["kubernetes"]["default_serviceaccount"] = "python-pipelines"
        env["general"] = {}
        env["general"]["relocated_env"] = False
        env["general"]["secrets"] = []
        env["general"]["artifacts_dir_name"] = ".artifacts"
        env["general"]["artifacts_path"] = tempfile.mkdtemp()
        cls.kubernetes_api: client.CoreV1Api = env["kubernetes"]["api"]
        cls.namespace = env["kubernetes"]["default_namespace"]
    
    @classmethod
    def tearDownClass(cls):
        print("Clearing the environmet")
        shutil.rmtree(env["general"]["artifacts_path"])
        env.clear()
