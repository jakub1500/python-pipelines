import unittest
from utils.common import generate_random_string, encode_str_to_base64
from k8s.secret import SecretUserPassword
from kubernetes import client
from tests.integration_tests.generic_test import GenericTest
from kubernetes.client.models import v1_secret



class SecretTests(GenericTest):
    username = "kartoszka"
    password = "marchewkowa"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_secret_name = f"test-secret-{generate_random_string(10)}"
        secret_data = {"username": encode_str_to_base64(cls.username),
                        "password": encode_str_to_base64(cls.password)}
        test_secret : v1_secret.V1Secret = v1_secret.V1Secret(data=secret_data)
        test_secret.metadata = client.V1ObjectMeta(name=cls.test_secret_name)
        cls.kubernetes_api.create_namespaced_secret(cls.namespace, body=test_secret)

    @classmethod
    def tearDownClass(cls):
        cls.kubernetes_api.delete_namespaced_secret(cls.test_secret_name, cls.namespace)
        super().tearDownClass()

    def test_with_SecretUserPassword(self):
        """
        Test to verify if we can use kubernetes secrets with `with` clause.
        """
        with SecretUserPassword(self.test_secret_name, self.namespace) as secretUserPassword:
            self.assertEqual(self.username, secretUserPassword.username, f"username filed of secretUserPassword should equal {self.username}")
            self.assertEqual(self.password, secretUserPassword.password, f"password filed of secretUserPassword should equal {self.password}")

    def test_masked_in_logs_SecretUserPassword(self):
        """
        Test to verify is kubernetes secrets are masked while logging.
        """
        def test_logger_masking(text):
            self.assertFalse(test_value in text, "Tested secret wasn't masked!")
            self.assertTrue("*"*len(test_value) in text, "Tested secret wasn't masked!")

        def test_logger_not_masking(text):
            self.assertTrue(test_value in text, "Normal non-secret text was masked!")
            self.assertFalse("*"*len(test_value) in text, "Normal non-secret text was masked!")

        from utils.logger import Logger, logger

        # test Logger.debug
        old_logger = logger.debug
        
        test_value = self.username
        logger.debug = test_logger_masking
        with SecretUserPassword(self.test_secret_name, self.namespace) as secretUserPassword:
            Logger.debug(f"The username is {secretUserPassword.username}")

        logger.debug = test_logger_not_masking
        test_value = "ogorek"
        Logger.debug(f"The username is {test_value}")

        logger.debug = old_logger

        # test Logger.info
        old_logger = logger.info
        
        test_value = self.username
        logger.info = test_logger_masking
        with SecretUserPassword(self.test_secret_name, self.namespace) as secretUserPassword:
            Logger.info(f"The username is {secretUserPassword.username}")

        logger.info = test_logger_not_masking
        test_value = "ogorek"
        Logger.info(f"The username is {test_value}")

        logger.info = old_logger

        # test Logger.warning
        old_logger = logger.warning
        
        test_value = self.username
        logger.warning = test_logger_masking
        with SecretUserPassword(self.test_secret_name, self.namespace) as secretUserPassword:
            Logger.warning(f"The username is {secretUserPassword.username}")

        logger.warning = test_logger_not_masking
        test_value = "ogorek"
        Logger.warning(f"The username is {test_value}")

        logger.warning = old_logger

        # test Logger.error
        old_logger = logger.error
        
        test_value = self.username
        logger.error = test_logger_masking
        with SecretUserPassword(self.test_secret_name, self.namespace) as secretUserPassword:
            Logger.error(f"The username is {secretUserPassword.username}")

        logger.error = test_logger_not_masking
        test_value = "ogorek"
        Logger.error(f"The username is {test_value}")

        logger.error = old_logger  


if __name__=='__main__':
    unittest.main()