"""Module defining the MVC for MLIP workflow configuration."""

import aiidalab_widgets_base as awb
import ipywidgets as ipw
import traitlets as tl
from aiida.orm import SinglefileData

from aiidalab_alc.common.file_handling import FileUploadWidget, FilenameSelector, create_filename_selector

class MLIPWorkflowModel(tl.HasTraits):
    """The model for setting up a MLIP workflow."""

    calc_style = tl.Unicode("NONE", allow_none=False)
    optimisation = tl.Unicode("NONE", allow_none=False)
    maximum_force= tl.Float("NONE", allow_none=False)
    pressure = tl.Float("NONE", allow_none=False)
    force_field = tl.Unicode(" ", allow_none=True)
    submitted = tl.Bool(False).tag(sync=True)
    use_dftd3 = tl.Bool(False).tag(sync=True)

    default_guide = ""


class MethodWizardStep(ipw.VBox, awb.WizardAppWidgetStep):
    """Wizard setup for the calculation workflow."""

    def __init__(self, model: MLIPWorkflowModel, **kwargs):
        """
        MethodWizardStep constructor.

        Parameters
        ----------
        model : MLIPWorkflowModel
            The model that defines the data related to this step in the setup wizard.
        **kwargs :
            Keyword arguments passed to the parent class's constructor.
        """
        super().__init__(children=[], **kwargs)
        self.model = model
        self.rendered = False

        return
    
    def render(self):
        """Render the wizard contents if not already rendered."""
        if self.rendered:
            return

        self.header = ipw.HTML(
            """
            <h3> MLIP Calculation </h3>
            """,
            layout={"margin": "auto"},
        )
        self.guide = ipw.HTML(
            self.model.default_guide,
        )

        self.options_widget = MLIPOptionsWidget(self.model)
        #ipw.dlink((self.options_widget.ff_file, "file"), (self.model, "force_field"))

        self.submit_btn = ipw.Button(
            description="Submit Options",
            disbled=False,
            button_style="success",
            tooltip="Submit the workflow configuration",
            icon="check",
            layout={"margin": "auto", "width": "60%"},
        )
        self.submit_btn.on_click(self._submit)

        self.children = [self.header, self.guide, self.options_widget, self.submit_btn]
        self.rendered = True
        return

    def _submit(self, _):
        """Store the MLIP parameters in the MLIP workflow model."""
        self.model.calc_style = self.options_widget.calculation_dropdown.value
        self.model.optimisation = self.options_widget.optimisation_dropdown.value

        try:
            self.model.maximum_force = float(self.options_widget.max_force_text.value)
        except ValueError:
            self.model.maximum_force.clear()
            self.options_widget.max_force_text.value = "0.001"
        except Exception as e:
            raise e
        
        try:
            self.model.pressure = float(self.options_widget.pressure_text.value)
        except ValueError:
            self.model.pressure.clear()
            self.options_widget.pressure_text.value = "0.0"
        except Exception as e:
            raise e
        
        if not self.model.force_field:
            print("ERROR: No MLIP file found...", self.model.force_field)
            return
        self.submit_btn.description = "Submitted"
        self.submit_btn.disabled = True
        self.options_widget.disable(True)
        return

class MLIPOptionsWidget(ipw.VBox):
    """Widget for selecting the MLIP input options."""

    def __init__(self, model: MLIPWorkflowModel, **kwargs):
        """
        MLIPOptionsWidget constructor.

        Parameters
        ----------
        model : MLIPWorkflowModel
            The model that defines the data related to this step in the setup wizard.
        **kwargs :
            Keyword arguments passed to the parent class's constructor.
        """
        super().__init__(**kwargs)
        self.model = model
        self.rendered = False

        self.calculation_dropdown = ipw.Dropdown(
            options=["Geometry optimisation", "Single point"],
            description="Calculation:",
            disabled=False,
            layout={"width": "50%"},
        )
        self.calculation_dropdown.observe(self._update_optimisation, names='value')
        
        self.optimisation_dropdown = ipw.Dropdown(
            options=["cell lengths", "fully relax", "atoms only"],
            description="Optimisation:",
            disabled=False,
            layout={"width": "50%"},
        )
        
        self.enable_dftd3_chk = ipw.Checkbox(
            value=False, description="Use DFTd3", indent=True
        )
                
        self.pressure_text = ipw.Text(
            value="0.0",
            description="Pressure:",
            disabled=False,
            layout={"width": "50%"},
        )
        self.max_force_text = ipw.Text(
            value="0.001",
            description="Max force:",
            disabled=False,
            layout={"width": "50%"},
        )

        self.arch_dropdown = ipw.Dropdown(
            options=["mace"],
            description="Architecture:",
            disabled=False,
            layout={"width": "50%"},
        )

        self.ff_file = create_filename_selector(label="Model filename:", placeholder="mace_mp_small.model", 
                                        default = "mace_mp_small.model")
    
        self.ff_file.observe(self.on_filename_change, names="filename")
        
        self.children = [
            self.calculation_dropdown,
            self.optimisation_dropdown,
            self.enable_dftd3_chk,
            self.pressure_text,
            self.max_force_text,
            self.arch_dropdown,
            self.ff_file,
        ]

        # self.layout = Layout(margin="auto")

        return
    
    def on_filename_change(self, change):
        self.model.force_field = self.ff_file.value

    def _on_file_upload(self, change):
        """When file upload button is pressed."""
        #self.output.clear_output()
        print("change", change)
        uploaded = change["new"]
        if not uploaded:
            self.status.value = "<i>No file uploaded yet.</i>"
            return
        self.ff_file.disable(True)
        self._update_children()
        return
    
    def _get_mm_theory_options(self) -> list[str]:
        """Get the available MM theory options."""
        try:
            from aiida_MLIP.utils import MLIPMMTheory

            return list(MLIPMMTheory.__members__.keys())
        except ImportError:
            return []
        except Exception as e:
            raise e

    #def _enable_dftd3_options(self, _) -> None:
    #    self.pressure_text.disabled = not self.enable_dftd3_chk.value
    #    self.max_force_text.disabled = not self.enable_dftd3_chk.value
    #    self.ff_file.disable(not self.enable_dftd3_chk.value)
    #    return

    def _update_optimisation(self, _) -> None:
        if self.calculation_dropdown.value.lower() == "geometry optimisation":
            self.optimisation_dropdown.disabled = False
            self.pressure_text.disabled = False
            self.max_force_text.disabled = False
        else:
            self.optimisation_dropdown.disabled = True
            self.pressure_text.disabled = True
            self.max_force_text.disabled = True
        return

    def render(self):
        """Render the options widget contents if not already rendered."""
        if self.rendered:
            return

        self.rendered = True
        return

    def disable(self, val: bool) -> None:
        """Disable the input fields."""
        for child in self.children:
            child.disabled = val
        #self.ff_file.disable(val)
        return
