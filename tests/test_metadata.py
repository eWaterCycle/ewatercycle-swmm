"""Lightweight checks that need neither ewatercycle nor a container.

These only read the repo's own files, so they run anywhere (CI, a bare
checkout, a machine without Docker) and should always pass.
"""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_version_is_present_and_semver():
    init = _read("src/ewatercycle_swmm/__init__.py")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    assert match, "no __version__ found in package __init__.py"
    assert re.fullmatch(r"v?\d+\.\d+\.\d+", match.group(1)), match.group(1)


def test_plugin_entry_point_registered():
    pyproject = tomllib.loads(_read("pyproject.toml"))
    models = pyproject["project"]["entry-points"]["ewatercycle.models"]
    assert models.get("SWMM") == "ewatercycle_swmm.model:SWMM"


def test_container_image_reference_is_well_formed():
    src = _read("src/ewatercycle_swmm/model.py")
    match = re.search(
        r'"(ghcr\.io/ewatercycle/swmm-grpc4bmi:v\d+\.\d+\.\d+)"', src
    )
    assert match, "container image reference missing or malformed"


def test_example_inp_present_with_required_sections():
    inp = _read("example.inp")
    for section in ("[OPTIONS]", "[SUBCATCHMENTS]", "[RAINGAGES]"):
        assert section in inp, f"example.inp is missing the {section} section"
    assert "FLOW_UNITS" in inp
