import sys

import pytest
from unittest import mock
from typing import List

from ci.ray_ci.docker import run_command


def test_run_command() -> None:
    command = ["run", "command"]

    def _mock_check_output(input: List[str]) -> None:
        input_str = " ".join(input)
        assert "/bin/bash -ic run command" in input_str

    with mock.patch("subprocess.check_output", side_effect=_mock_check_output):
        run_command(command)


if __name__ == "__main__":
    sys.exit(pytest.main(["-v", __file__]))
