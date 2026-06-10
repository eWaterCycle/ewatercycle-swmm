# ewatercycle-swmm

An [eWaterCycle](https://ewatercycle.readthedocs.io/) plugin for the EPA **Storm
Water Management Model (SWMM)**.

This plugin wraps the [pySWMM](https://www.pyswmm.org/) `Simulation` object in
the [Basic Model Interface (BMI)](https://bmi.readthedocs.io/) and runs it inside
a [grpc4bmi](https://grpc4bmi.readthedocs.io/) container, so SWMM can be driven
step-by-step from Python and coupled to other models in the eWaterCycle
framework.

The containerized BMI model lives in a separate repository:
[eWaterCycle/swmm-bmi](https://github.com/eWaterCycle/swmm-bmi). This plugin only
provides the thin eWaterCycle wrapper around the published container image
(`ghcr.io/ewatercycle/swmm-grpc4bmi`).

## What is SWMM?

SWMM is the EPA's dynamic rainfall-runoff simulation model, used for single-event
or long-term simulation of runoff quantity and quality, primarily in urban areas.
A SWMM model represents the drainage network as **subcatchments**, **nodes**
(junctions, outfalls, storage), **links** (conduits, pumps, weirs) and **rain
gages**.

[pySWMM](https://www.pyswmm.org/) is an open-source tool that provides "Pythonic"
access to the SWMM data model. Its `Simulation` object lets you step through a
running simulation, read and modify network state at each step, and post-process
results without manipulating SWMM input files directly. eWaterCycle has wrapped
this `Simulation` object in BMI — so for the most part you can use the model as
if it were a pySWMM `Simulation`, but through the standardized BMI calls
(`initialize`, `update`, `get_value`, `set_value`, `finalize`).

> Cite pySWMM: McDonnell, B., Ratliff, K., Tryby, M., Wu, J. X., & Mullapudi, A.
> (2020). *PySWMM: The Python Interface to Stormwater Management Model (SWMM)*.
> https://doi.org/10.21105/joss.02292

## Installation

Install this package alongside your eWaterCycle installation:

```console
pip install ewatercycle-swmm
```

SWMM then becomes available as one of the eWaterCycle models:

```python
from ewatercycle.models import SWMM
```

The container image is pulled automatically the first time you run the model, so
a working container runtime (Docker or Apptainer, as configured in eWaterCycle)
is required.

## Input data

To run the model you need a SWMM input file (`example.inp`). This file describes
the drainage network and the simulation options. It can be created with QGIS via
the [generate_swmm_inp](https://github.com/Jannik-Schilling/generate_swmm_inp)
plugin, or with any other SWMM model builder.

> **Note:** if your model uses an external time series data file, it currently
> has to share the name of the `.inp` file (i.e. `example.dat` next to
> `example.inp`). It is picked up automatically when present.

The input file is provided to eWaterCycle through a `ParameterSet`:

```python
from pathlib import Path
from ewatercycle.base.parameter_set import ParameterSet

swmm_dir = Path.home() / "ewatercycle-swmm"
input_file = swmm_dir / "example.inp"

parameters = ParameterSet(
    name="SWMM_parameter_files",
    directory=swmm_dir,
    config=input_file,
    target_model="swmm",
)
```

## Usage

A worked example is provided in
[`demo_containerized_model.ipynb`](demo_containerized_model.ipynb), which
reproduces the "Latte" example from the pySWMM website (`example.inp`). The
essentials:

### Set up and initialize

```python
from ewatercycle.models import SWMM

model = SWMM(parameter_set=parameters)
cfg_file, _ = model.setup()
model.initialize(cfg_file)
```

### The model grids

SWMM exposes its elements through four BMI grids:

| Grid | Element type   |
|------|----------------|
| 0    | Subcatchments  |
| 1    | Nodes          |
| 2    | Links          |
| 3    | Rain gages     |

```python
n_sc    = model.get_grid_size(0)  # subcatchments
n_nodes = model.get_grid_size(1)  # nodes
n_links = model.get_grid_size(2)  # links
```

### Reading values: the time loop

The model is advanced one step at a time with `update()`, reading variables with
`get_value()` along the way — the standard BMI pattern:

```python
import numpy as np

times, node_depth, link_flow = [], [], []

while model.time < model.end_time:
    times.append(model.get_current_time())
    node_depth.append(model.get_value("node_depth"))
    link_flow.append(model.get_value("link_flow"))
    model.update()

node_depth = np.array(node_depth)  # shape: (n_steps, n_nodes)
link_flow  = np.array(link_flow)   # shape: (n_steps, n_links)
```

#### Output variables

| Variable               | Grid          | Units  |
|------------------------|---------------|--------|
| `subcatchment_runoff`  | subcatchments | m³/s   |
| `node_depth`           | nodes         | m      |
| `node_flooding`        | nodes         | m³/s   |
| `link_flow`            | links         | m³/s   |

### Setting values: external forcing

Input variables can be set with `set_value()` before each `update()`, for
example to inject a lateral inflow at every node:

```python
EXTERNAL_INFLOW_M3S = 0.05  # 50 L/s at every node, on top of storm runoff

while model.get_current_time() < model.get_end_time():
    model.set_value("node_lateral_inflow", np.full(n_nodes, EXTERNAL_INFLOW_M3S))
    model.update()
```

#### Input variables

| Variable               | Grid  | Units                                  |
|------------------------|-------|----------------------------------------|
| `node_lateral_inflow`  | nodes | m³/s (via pySWMM `Node.generated_inflow`) |
| `precipitation`        | rain gages | in/hr or mm/hr (depends on flow units) |

### Finalize

Always finalize the model when you are done. This shuts down the underlying
container so it does not keep running in the background and consuming resources:

```python
model.finalize()
```

## How it works

- [`SWMM`](src/ewatercycle_swmm/model.py) is a `ContainerizedModel` that points
  at the `ghcr.io/ewatercycle/swmm-grpc4bmi` image built from
  [eWaterCycle/swmm-bmi](https://github.com/eWaterCycle/swmm-bmi).
- `setup()` stages the `.inp` (and optional `.dat`) file into a run directory and
  writes a `swmm_config.json` configuration file that the container reads on
  `initialize()`.
- Any attribute eWaterCycle does not expose itself is delegated to the underlying
  BMI/pySWMM `Simulation` object, so you can largely treat the model like a
  pySWMM `Simulation`.

For the BMI implementation, the container build, and the full list of exposed
variables, see the [swmm-bmi repository](https://github.com/eWaterCycle/swmm-bmi).

## License

`ewatercycle-swmm` is distributed under the terms of the
[Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) license.
