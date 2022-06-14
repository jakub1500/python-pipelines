
class JobExcpetion(Exception):
    pass

"""
Job initializing exceptions
"""

class JobNotFoundException(JobExcpetion):
    pass

class JobParameterMissingException(JobExcpetion):
    pass

class JobParameterTypeMismatchException(JobExcpetion):
    pass

"""
Job flow exceptions
"""

class JobFailedException(JobExcpetion):
    pass


from enum import Enum

class JobResult(Enum):
    PASS = 1
    FAILED = 2
    UNSTABLE = 3

def select_job(job_name: str, job_parameters: str):
    if job_name == "Build_Bash":
        from jobs.build_bash import BuildBashJob
        return BuildBashJob(job_parameters)
    else:
        raise JobNotFoundException(f"Could not find job with given name '{job_name}'")
