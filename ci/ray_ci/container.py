import os
import subprocess
import sys
import tempfile

from typing import List

from ci.ray_ci.utils import chunk_into_n

DOCKER_ECR = "029272617770.dkr.ecr.us-west-2.amazonaws.com"
DOCKER_REPO = "ci_base_images"
DOCKER_TAG = f"oss-ci-build_{os.environ.get('BUILDKITE_COMMIT')}"
ROOT_DIR = "/ray/ci/ray_ci"


def run_tests(
    team: str,
    test_targets: List[str],
    parallelism,
) -> bool:
    """
    Run tests parallelly in docker.  Return whether all tests pass.
    """
    chunks = chunk_into_n(test_targets, parallelism)
    _setup_test_environment(team)
    runs = [_run_tests_in_docker(chunk) for chunk in chunks]
    exits = [run.wait() for run in runs]
    return all(exit == 0 for exit in exits)


def _setup_test_environment(team: str) -> None:
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"
    subprocess.check_call(
        [
            "docker",
            "build",
            "--build-arg",
            f"BASE_IMAGE={_get_docker_image()}",
            "--build-arg",
            f"TEST_ENVIRONMENT_SCRIPT={team}.tests.env.sh",
            "-t",
            _get_docker_image(),
            "-f",
            f"{ROOT_DIR}/tests.env.Dockerfile",
            ROOT_DIR,
        ],
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )


def _run_tests_in_docker(test_targets: List[str]) -> subprocess.Popen:
    command = f"bazel test --config=ci {' '.join(test_targets)}"
    return subprocess.Popen(_docker_run_bash_script(command))


def run_command(script: str) -> bytes:
    """
    Run command in docker
    """
    return subprocess.check_output(_docker_run_bash_script(script))


def _docker_run_bash_script(script: str) -> str:
    return _get_docker_run_command() + ["/bin/bash", "-ice", script]


def docker_login() -> None:
    """
    Login to docker with AWS credentials
    """
    subprocess.run(["pip", "install", "awscli"])
    password = subprocess.check_output(
        ["aws", "ecr", "get-login-password", "--region", "us-west-2"],
        stderr=sys.stderr,
    )
    with tempfile.TemporaryFile() as f:
        f.write(password)
        f.flush()
        f.seek(0)

        subprocess.run(
            [
                "docker",
                "login",
                "--username",
                "AWS",
                "--password-stdin",
                DOCKER_ECR,
            ],
            stdin=f,
            stdout=sys.stdout,
            stderr=sys.stderr,
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