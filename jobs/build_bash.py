from .generic_job import GenericJob
from k8s.pod import Pod
from utils.logger import Logger

class BuildBashJob(GenericJob):

    mandatory_parameters = {
        "version": str
        # "author": str,
        # "debug": None
    }

    def content(self):
        Logger.info(f"The version parameter is {self.parameters['version']}")
        with Pod("ubuntu2204") as ubuntu:
            ubuntu.exec("apt update && apt install -y build-essential wget", silent=True)
            ubuntu.exec("wget https://ftp.gnu.org/gnu/bash/bash-5.1.8.tar.gz && tar -xf bash-5.1.8.tar.gz", silent=True)
            ubuntu.exec("cd bash-5.1.8 && ./configure && make")
            output = ubuntu.exec("bash-5.1.8/bash --version")["output"]
            correct_version = True if "GNU bash, version 5.1.8" in output else False
            print(f"Built correct version? {correct_version}")
            if not correct_version:
                self.fail_job("Built bash version is not correct!")