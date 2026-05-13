"""Module for handling AiiDA processes."""

import traitlets as tl
from aiida.engine import submit
from aiida.orm import Dict, load_code
from ipywidgets import dlink

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

        self.process = None

        return

    def _submit_model(self, _) -> None:
        """Handle the submission of the AiiDA process."""
        if MLIPProcess.validate_model(self):
            self.process = MLIPProcess(self)
            self.process.submit_process()
            self.block_results = False
            self.results_model.process_uuid = "1" #self.process.node.uuid
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

        code = load_code(self.model.resource_model.code_label)
        structure = self.model.structure_model.structure

        model_file = self.model.workflow_model.force_field
        print("force filed", self.model.workflow_model.force_field)
        architecture="mace"
        model = ModelData.from_local(model_file, architecture=architecture)

        inputs_geom = {
        "code": code,
        "model": model,
        "struct": structure,
        "device": Str("cpu"),
        "fmax": self.model.workflow_model.maximum_force,
        "opt_cell_lengths": Bool(True),
        "opt_cell_fully": Bool(True),
        "metadata": {"options": {"resources": {"num_machines": 1}}},
        }
        
        geomoptCalc = CalculationFactory("mlip.opt")

        wg = WorkGraph("GeomOptPhonGraph")

        gm_calc = wg.add_task(
            geomoptCalc,
            name="geomopt_calc",
            **inputs_geom
        )

        #opt_struct = gm_calc.outputs.final_structure
        wg.outputs.results = wg.tasks.geomopt_calc.outputs.results_dict
        wg.outputs.results_file = wg.tasks.geomopt_calc.outputs.xyz_output

        wg.run()

        #wg.outputs.results.value.get_dict()
        
        return
