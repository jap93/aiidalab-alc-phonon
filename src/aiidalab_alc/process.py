"""Module for handling AiiDA processes."""

import traitlets as tl
from aiida.engine import submit
from aiida.orm import Dict, load_code
from ipywidgets import dlink
from pathlib import Path
from aiida_mlip.data.model import ModelData
from aiida.orm import StructureData
from aiida.orm import load_code
from aiida.orm import Str, Float, Bool, Int
from aiida.plugins import CalculationFactory
from aiida_workgraph import WorkGraph

from aiidalab_alc.resources import ComputationalResourcesModel
from aiidalab_alc.results import ResultsModel
from aiidalab_alc.structure import StructureStepModel
from aiidalab_alc.workflow import MLIPWorkflowModel

from ase import Atoms
import numpy as np

class MainAppModel(tl.HasTraits):
    """The main AiiDAlab application MVC model."""

    block_results = tl.Bool(True, allow_none=False)

    def __init__(self):
        """MainAppModel constructor."""
        super().__init__()
        self.structure_model = StructureStepModel()
        self.workflow_model = MLIPWorkflowModel()
        self.resource_model = ComputationalResourcesModel()
        self.results_model = ResultsModel()

        self.resource_model.observe(self._submit_model, "submitted")
        dlink((self, "block_results"), (self.results_model, "blocked"))
        print("resuly_model", self.results_model.process_uuid)
        self.process = None

        return

    def _submit_model(self, _) -> None:
        """Handle the submission of the AiiDA process."""
        if MLIPProcess.validate_model(self):
            self.process = MLIPProcess(self)
            self.process.submit_process()
            self.block_results = False

            self.results_model.process_uuid = self.process.node.uuid
            print("_submit_model: process node ", self.process.node.uuid, "results model process uuid", self.results_model.process_uuid)
            
        else:
            print("ERROR: Input Validation Failed")
        return

    def reset(self) -> None:
        """Reset the state of the model."""
        self.submitted = False


class MLIPProcess:
    """Class to handle a MLIP AiiDA process."""

    def __init__(self, model: MainAppModel):
        """
        MLIPProcess constructor.

        Parameters
        ----------
        model : MainAppModel
            The main application model containing all necessary data.
        """
        self.model = model
        self.node = None
        return

    @classmethod
    def validate_model(cls, model: MainAppModel) -> bool:
        """
        Validate the main application model.

        Parameters
        ----------
        model : MainAppModel
            The main application model to validate.

        Returns
        -------
        bool
            True if the model is valid, False otherwise.
        """
        if not model.structure_model.has_structure:
            if not model.structure_model.has_file:
                print("No structure provided.")
                return False
            
        if not model.workflow_model.force_field:
            print("No force field provided.")
            return False
        
        # Add more validation checks as needed
        return True

    def submit_process(self):
        """Submit the AiiDA process."""
        code = load_code(self.model.resource_model.code_name)
        print("code", code)
        device = self.model.resource_model.device_name
        print("device", device)        
        structure = StructureData(ase=self.model.structure_model.structure.get_ase())
        
        print("structure", structure)
        model_file = self.model.workflow_model.force_field
        if not Path(model_file).exists():
            print("model file does not exist", model_file)
        print("model file", model_file)
        architecture = self.model.workflow_model.architecture
        mlip_model = ModelData.from_local(model_file, architecture=architecture)

        calculation_style = self.model.workflow_model.calc_style.lower()
        optimisation = self.model.workflow_model.optimisation.lower()
        print("calc_style", calculation_style, "optimisation", optimisation)
        
        if calculation_style == "geometry optimisation":
            inputs_geom = {
                "code": code,
                "model": mlip_model,
                "struct": structure,
                "device": Str(device),
                "fmax": Float(self.model.workflow_model.maximum_force),
                "metadata": {"options": {"resources": {"num_machines": 1}}},
            }

            if optimisation == "cell lengths":
                inputs_geom["opt_cell_lengths"] = Bool(True)
            else:
                inputs_geom["opt_cell_fully"] = Bool(True)

            print("inputs",inputs_geom)
        
            geomoptCalc = CalculationFactory("mlip.opt")

        else: # must be single point
            inputs_geom = {
                "code": code,
                "model": mlip_model,
                "struct": structure,
                "device": Str("cpu"),
                "metadata": {"options": {"resources": {"num_machines": 1}}},
            }
        
            geomoptCalc = CalculationFactory("mlip.sp")

        wg = WorkGraph("GeomOptPhonGraph")

        wg.add_task(
            geomoptCalc,
            name="geomopt_calc",
            **inputs_geom
        )

        wg.outputs.results = wg.tasks.geomopt_calc.outputs.results_dict
        wg.outputs.results_file = wg.tasks.geomopt_calc.outputs.xyz_output

        wg.tasks.geomopt_calc

        wg.run()

        type(wg.outputs.results_file.value)

        print("outputs", wg.outputs)

        print("results", wg.outputs.results.value.get_dict())
        self.model.results_model.final_structure = StructureData(ase=self.dict_to_ase_atoms(wg.outputs.results.value.get_dict()))
        print("results_file", wg.outputs.results_file.value)
        self.node = wg.outputs.results_file.value


        if wg.process.is_failed:
            print("WorkGraph failed")

        if wg.process.exit_status != 0:
            print(f"Failed with exit status {wg.process.exit_status}")

        # optional, if supported
        if hasattr(wg.process, "exit_message"):
            print(f"WorkGraph exit message: {wg.process.exit_message}")

        # Map outputs to the WorkGraph
        #wg.outputs.results = wg.tasks.geomopt_calc.outputs.results_dict
        #print("results", wg.outputs.results)

        #self.node = wg.nodes[0]
        #print(f"WorkGraph complete: {self.node.uuid}")
        return
    
    


    def dict_to_ase_atoms(self, data: dict) -> Atoms:
        atoms = Atoms(
            numbers=np.asarray(data["numbers"], dtype=int),
            positions=np.asarray(data["positions"], dtype=float),
            cell=np.asarray(data["cell"], dtype=float),
            pbc=tuple(data["pbc"]),
        )

        if "masses" in data:
            atoms.set_masses(np.asarray(data["masses"], dtype=float))

        if "info" in data:
            atoms.info.update(data["info"])

        if "mace_forces" in data:
            atoms.arrays["mace_forces"] = np.asarray(data["mace_forces"], dtype=float)

        return atoms
