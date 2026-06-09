"""eWaterCycle wrapper for the LeakyBucket model."""
import json
from collections.abc import ItemsView
from pathlib import Path
from typing import Any
import os
from shutil import copy2

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
        # self._config["inp_file"] = str(self.parameter_set["config"]["inp_file"])
        # self._config["data_file"] = str(self.parameter_set["config"]["data_file"])

        # self._config["inp_file"] = str(self.parameter_set.config)
        # data_file = str(self.parameter_set.config).replace(".inp", ".data")
        # if Path(data_file).exists():
        #     self._config["data_file"] = data_file

        # out_file = str(self.parameter_set.config).replace(".inp", ".out")
        # self._config["out_file"] = out_file

        # rpt_file = str(self.parameter_set.config).replace(".inp", ".rpt")
        # self._config["rpt_file"] = rpt_file
        
        # for kwarg in kwargs:  # Write any kwargs to the config.
        #     self._config[kwarg] = kwargs[kwarg]

        run_dir = self._cfg_dir.resolve()

        source_inp = Path(self.parameter_set.config).resolve()
        inp_file = self._stage_input_files(source_inp, run_dir)
        
        # inp_file = run_dir / Path(self.parameter_set.config).name
        data_file = inp_file.with_suffix(".data")

        self._config["inp_file"] = str(inp_file)

        # TODO: For now the data file has to have the same name as the .imp file
        if data_file.exists():
            self._config["data_file"] = str(data_file)

        for kwarg in kwargs:  # Write any kwargs to the config.
            self._config[kwarg] = kwargs[kwarg]
        
        # for kwarg, value in kwargs.items():
        #     self._config[kwarg] = value

        config_file = self._cfg_dir / "swmm_config.json"

        with config_file.open(mode="w") as f:
            f.write(json.dumps(self._config, indent=4))

        return config_file

    def _stage_input_files(self, inp_file: Path, run_dir: Path) -> Path:
        staged_inp = run_dir / inp_file.name
        copy2(inp_file, staged_inp)
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

    # ensures that bmi is called instead of the pySWMM simulation object
    # def __getattr__(self, name):
    #     bmi = self.__dict__.get("_bmi", None)
    
    #     if bmi is not None and hasattr(bmi, name):
    #         return getattr(bmi, name)
    
    #     raise AttributeError(name)
    
class SWMM(ContainerizedModel, SWMMMethods):
    """The SWMM eWaterCycle model, with the Container Registry docker image."""
    bmi_image: ContainerImage = ContainerImage(
        "ghcr.io/ewatercycle/swmm-grpc4bmi:v0.0.3"
    )

    # ensures that bmi is called instead of the pySWMM simulation object
    # def __getattr__(self, name):
    #     bmi = self.__dict__.get("_bmi", None)
    
    #     if bmi is None:
    #         raise AttributeError(
    #             f"{name} not available yet: BMI not initialized (call setup() first)"
    #         )
    
    #     return getattr(bmi, name)

    # def __getattr__(self, name):
    #     bmi = self.__dict__.get("_bmi", None)
    
    #     if bmi is not None and hasattr(bmi, name):
    #         return getattr(bmi, name)
    
    #     raise AttributeError(name)

# class SWMMLocal(LocalModel, SWMMMethods):
#     """The HBV eWaterCycle model, with the local BMI."""
#     bmi_class: Type[Bmi] = import_bmi()
