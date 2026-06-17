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
        source_inp = Path(self.parameter_set.config).resolve()
        inp_file = source_inp

        self._config["inp_file"] = str(inp_file)

        report_file = self._cfg_dir / "report_file.rpt"
        output_file = self._cfg_dir / "output_file.out"

        for kwarg, value in kwargs.items():
            self._config[kwarg] = str(value)

        self._config["report_file"] = str(report_file)
        self._config["output_file"] = str(output_file)
        
        config_file = self._cfg_dir / "swmm_config.json"
        with config_file.open(mode="w") as f:
            f.write(json.dumps(self._config, indent=4))

        return config_file

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
        "ghcr.io/ewatercycle/swmm-grpc4bmi:v0.0.4"
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