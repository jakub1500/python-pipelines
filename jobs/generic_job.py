from utils.logger import Logger
from . import JobResult
from . import JobParameterMissingException, JobParameterTypeMismatchException, JobFailedException
from abc import ABC, abstractmethod

class GenericJob(ABC):
    mandatory_parameters = {}

    def __init__(self, parameters: dict):
        self.parameters = parameters

    def set_up(self):
        Logger.info("Running the setUp")

    def tear_down(self):
        Logger.info("Running the tearDown")

    @abstractmethod
    def content(self):
        pass

    def _verify_job_parameters(self):
        """
        Each job which inherits from GenericJob class may declare mandatory parameters
        for its to run. Moreover each parameter can be expected as specific type.
        Currently supported types are [str, int, bool] and if parameter can be any type
        [None]
        """
        for parameter_name, parameter_type in self.mandatory_parameters.items():
            if parameter_name not in self.parameters.keys():
                raise JobParameterMissingException(
                    f"This job requires the '{parameter_name}' parameter!")
            if type(self.parameters[parameter_name]) != parameter_type and parameter_type is not None:
                raise JobParameterTypeMismatchException(
                    f"Parameter {parameter_name} " +
                    f"should have type '{parameter_type}', " +
                    f"but was '{type(self.parameters[parameter_name])}'")

    def fail_job(self, description: str=""):
        raise JobFailedException(description)

    def run(self):
        job_result = JobResult.FAILED
        self._verify_job_parameters()
        try:
            self.set_up()
            self.content()
            job_result = JobResult.PASS
        finally:
            self.tear_down()

        return job_result