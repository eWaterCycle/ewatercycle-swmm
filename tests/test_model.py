"""Checks on the SWMM wrapper class.

These need ewatercycle (and its dependencies) importable, but they do NOT
start a container or run the model. If ewatercycle is not installed the whole
module is skipped rather than failed, so a bare environment stays green.
"""
import sys
from pathlib import Path

import pytest

pytest.importorskip("ewatercycle", reason="ewatercycle not installed")

# Import the wrapper the same way the demo notebook does (src is a namespace
# package when running from the repo root), without requiring an editable install.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ewatercycle_swmm.model import SWMM, SWMMMethods  # noqa: E402


def test_swmm_is_a_containerized_model():
    from ewatercycle.base.model import ContainerizedModel

    assert issubclass(SWMM, ContainerizedModel)


def test_swmm_points_at_the_swmm_image():
    assert "bmi_image" in SWMM.model_fields
    default = SWMM.model_fields["bmi_image"].default
    assert "swmm-grpc4bmi" in str(default)


def test_config_template_exposes_inp_file_key():
    # _config is a pydantic private attribute holding the default config dict.
    config_default = SWMMMethods.__private_attributes__["_config"].get_default()
    assert "inp_file" in config_default
