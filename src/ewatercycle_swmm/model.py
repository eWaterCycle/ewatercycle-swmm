"""eWaterCycle wrapper for the LeakyBucket model."""
import json
from collections.abc import ItemsView
from pathlib import Path
from typing import Any
import os
from shutil import copy2
from bmipy import Bmi
import shlex
import warnings

# from ewatercycle.base.forcing import GenericDistributedForcing
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.base.model import ContainerizedModel, eWaterCycleModel, LocalModel
from ewatercycle.container import ContainerImage

_FILE_KEYWORD_SECTIONS = {"RAINGAGES", "TIMESERIES", "TEMPERATURE"}

# def import_bmi():
#     """"Import BMI, raise useful exception if not found"""
#     try:
#         from ewatercycle.SWMM import SWMM as swmm_bmi
#     except ModuleNotFoundError:
#         msg = (
#             "SWMM bmi package not found, install using: `pip install ewatercycle-swmm`"
#         )
#         raise ModuleNotFoundError(msg)

#     return swmm_bmi

class SWMMMethods(eWaterCycleModel):
    """The eWatercycle SWMM model.
    """
    forcing: None  # The model does not require forcing.
    parameter_set: ParameterSet  # The model has no parameter set.

    _config: dict = {
        "inp_file": "",
    }

    def _make_cfg_file(self, **kwargs) -> Path:
        """Write model configuration file."""
        run_dir = self._cfg_dir.resolve()

        source_inp = Path(self.parameter_set.config).resolve()
        inp_file = self._stage_input_files(source_inp, run_dir)

        self._config["inp_file"] = str(inp_file)

        for kwarg, value in kwargs.items():
            self._config[kwarg] = value

        config_file = self._cfg_dir / "swmm_config.json"
        with config_file.open(mode="w") as f:
            f.write(json.dumps(self._config, indent=4))

        return config_file

    def _stage_input_files(self, inp_file: Path, run_dir: Path) -> Path:
        """Copy the .inp and every external data file it references into run_dir.

        SWMM resolves the relative file names inside the .inp against the
        process working directory, which for the grpc4bmi container is this
        mounted run_dir. Copying each referenced file in next to the .inp
        (under the same relative name) is what makes them findable.
        """
        staged_inp = run_dir / inp_file.name
        copy2(inp_file, staged_inp)

        for name in _find_referenced_files(inp_file):
            ref = Path(name)
            if ref.is_absolute():
                warnings.warn(
                    f"{inp_file.name} references an absolute path {name!r}; it "
                    "cannot be staged and will not resolve inside the container. "
                    "Use a path relative to the .inp instead."
                )
                continue
            source = inp_file.parent / ref
            if not source.exists():
                raise FileNotFoundError(
                    f"{inp_file.name} references data file {name!r}, "
                    f"but it was not found at {source}."
                )
            target = run_dir / ref
            target.parent.mkdir(parents=True, exist_ok=True)
            copy2(source, target)

        return staged_inp

    @property
    def parameters(self) -> ItemsView[str, Any]:
        return self._config.items()

    def finalize(self) -> None:
        """Perform tear-down tasks for the model.
    
        After finalization, the model should not be used anymore.
        """
        # remove bmi
        self._bmi.finalize()
        del self._bmi

    
class SWMM(ContainerizedModel, SWMMMethods):
    """The SWMM eWaterCycle model, with the Container Registry docker image."""
    bmi_image: ContainerImage = ContainerImage(
        "ghcr.io/ewatercycle/swmm-grpc4bmi:v0.0.3"
    )
    
    # Ensures that bmi is called instead of the pySWMM simulation object
    def __getattr__(self, name: str):
        # Never delegating dunders / pydantic internals -> avoids init-time recursion.
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        # 1) Let pydantic resolve fields + private attrs (incl. _bmi) first.
        try:
            return super().__getattr__(name)
        except AttributeError:
            pass
        # 2) Fall back to the BMI instance for anything eWaterCycle doesn't expose.
        private = object.__getattribute__(self, "__pydantic_private__")
        bmi = (private or {}).get("_bmi")
        if bmi is not None and hasattr(bmi, name):
            return getattr(bmi, name)
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )

# class SWMMLocal(LocalModel, SWMMMethods):
#     """The HBV eWaterCycle model, with the local BMI."""
#     bmi_class: Type[Bmi] = import_bmi()

def _find_referenced_files(inp_file: Path) -> list[str]:
    """Scan a SWMM .inp file for the external input files it depends on.

    Returns the names exactly as written in the .inp (normally relative to the
    .inp's own directory). Covers every FILE reference SWMM reads as input:
    rain gages, time series, the climate/temperature file, and interface files
    opened for reading ([FILES] ... USE ...). Output-only interface files
    ([FILES] ... SAVE ...) are skipped, since SWMM creates those itself.
    """
    referenced: set[str] = set()
    section: str | None = None

    with inp_file.open() as f:
        for raw in f:
            line = raw.split(";", 1)[0].strip()  # strip comments + whitespace
            if not line:
                continue
            if line.startswith("["):
                section = line[1:].split("]", 1)[0].strip().upper()
                continue

            try:
                tokens = [t.strip('"') for t in shlex.split(line, posix=False)]
            except ValueError:  # unbalanced quotes -> best effort
                tokens = line.split()

            if section == "FILES":
                # USE|SAVE  <type>  Fname  -> only USE files are inputs.
                if len(tokens) >= 3 and tokens[0].upper() == "USE":
                    referenced.add(tokens[2])
            elif section in _FILE_KEYWORD_SECTIONS:
                for i, tok in enumerate(tokens[:-1]):
                    if tok.upper() == "FILE":
                        referenced.add(tokens[i + 1])
                        break

    return sorted(referenced)
