"""eWaterCycle wrapper for the LeakyBucket model."""
import json
from collections.abc import ItemsView
from pathlib import Path
from typing import Any

# from ewatercycle.base.forcing import GenericDistributedForcing
from ewatercycle.base.parameter_set import ParameterSet
from ewatercycle.base.model import ContainerizedModel, eWaterCycleModel
from ewatercycle.container import ContainerImage


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

        self._config["inp_file"] = str(self.parameter_set.config)
        data_file = str(self.parameter_set.config).replace(".inp", ".data")
        if data_file.exists():
            self._config["data_file"] = data_file

        for kwarg in kwargs:  # Write any kwargs to the config.
            self._config[kwarg] = kwargs[kwarg]

        config_file = self._cfg_dir / "swmm_config.json"

        with config_file.open(mode="w") as f:
            f.write(json.dumps(self._config, indent=4))

        return config_file

    @property
    def parameters(self) -> ItemsView[str, Any]:
        return self._config.items()


class SWMM(ContainerizedModel, SWMMMethods):
    """The LeakyBucket eWaterCycle model, with the Container Registry docker image."""
    bmi_image: ContainerImage = ContainerImage(
        "ghcr.io/ewatercycle/swmm-grpc4bmi:v0.0.1"
    )
