import os
import subprocess

from typing import List

from ci.ray_ci.utils import chunk_into_n

DOCKER_ECR = "029272617770.dkr.ecr.us-west-2.amazonaws.com"
DOCKER_REPO = "ci_base_images"
DOCKER_TAG = f"oss-ci-build_{os.environ.get('BUILDKITE_COMMIT')}"


def run_tests(
    test_targets: List[str],
    pre_run_commands: List[str],
    parallelism,
) -> int:
    """
    Run tests parallelly in docker
    """
    chunks = chunk_into_n(test_targets, parallelism)
    runs = [_run_tests_in_docker(chunk, pre_run_commands) for chunk in chunks]
    exits = [run.wait() for run in runs]
    return 0 if all(exit == 0 for exit in exits) else 1


def _run_tests_in_docker(test_targets: List[str], pre_test_commands: List[str]) -> int:
    bazel_options = (
        run_command(["./ci/run/bazel_export_options"]).decode("utf-8").split()
    )
    bazel_command = ["bazel", "test", "--config=ci"] + test_targets + bazel_options
    command = "\n".join(pre_test_commands + [" ".join(bazel_command)])
    return subprocess.Popen(_get_docker_run_command() + ["/bin/bash", "-ic", command])


def run_command(command: List[str]) -> bytes:
    """
    Run command in docker
    """
    return subprocess.check_output(
        _get_docker_run_command() + ["/bin/bash", "-ic", " ".join(command)]
    )


def docker_login() -> None:
    p = subprocess.Popen(
        ["aws", "ecr", "get-login-password", "--region", "us-west-2"],
        stdout=subprocess.PIPE,
    )
    subprocess.run(
        [
            "docker",
            "login",
            "--username",
            "AWS",
            "--password-stdin",
            DOCKER_ECR,
        ],
        stdin=p.stdout,
    )


def _get_docker_run_command() -> List[str]:
    return [
        "docker",
        "run",
        "-i",
        "--rm",
        "--workdir",
        "/ray",
        "--shm-size=2.5gb",
        _get_docker_image(),
    ]


def _get_docker_image() -> str:
    """
    Get docker image for a particular commit
    """
    return f"{DOCKER_ECR}/{DOCKER_REPO}:{DOCKER_TAG}"
