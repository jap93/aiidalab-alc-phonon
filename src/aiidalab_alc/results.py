"""Module for defining widgets/models for viewing process progress and results."""

import json
from pathlib import Path
from typing import cast
import numpy as np

import aiidalab_widgets_base as awb
from aiida import plugins
import ipywidgets as ipw
import traitlets as tl
from aiida.common.exceptions import NotExistent
from aiida.orm import (
    BandsData,
    NodeLinksManager,
    ProcessNode,
    StructureData,
    XyData,
    load_node,
)
from aiidalab_widgets_base.viewers import BandsDataViewer

class ProcessModel(tl.HasTraits):
    """Model describing an AiiDA process."""

    process_uuid = tl.Unicode(None, allow_none=True)

    @property
    def process(self) -> ProcessNode | None:
        """Return the process node for the stored uuid."""
        if not self.process_uuid:
            return None
        try:
            return cast(ProcessNode, load_node(self.process_uuid))
        except NotExistent:
            return None

    @property
    def has_process(self) -> bool:
        """Return true if a valid process node is associated with the uuid."""
        return self.process is not None

    @property
    def inputs(self) -> NodeLinksManager | list:
        """Return the inputs for the process."""
        return self.process.inputs if self.has_process else []

    @property
    def outputs(self) -> NodeLinksManager | list:
        """Return the outputs for the process."""
        return self.process.outputs if self.has_process else []


class ResultsModel(ProcessModel):
    """MVC results step model."""

    blocked = tl.Bool(False)
    final_structure = tl.Instance(StructureData, allow_none=True)


class ResultsWizardStep(ipw.VBox, awb.WizardAppWidgetStep):
    """Wizard for viewing process progress and results."""

    def __init__(self, model: ResultsModel, **kwargs):
        """
        ResultsWizardStep constructor.

        Parameters
        ----------
        model : ResultsModel
            The model controlling required data.
        **kwargs :
            Keyword arguments passed to the parent class's constructor.
        """
        super().__init__(**kwargs)
        self.model = model
        self.rendered = False
        self.model.observe(self._on_process_uuid_change, "process_uuid")

    def _on_process_uuid_change(self, _):
        """Update view when process UUID changes."""
        if self.rendered:
            self._update_view()

    def load_json(self, filename: str):
        """Helper to load JSON data from a file relative to this script."""
        # Try to find the file relative to the package directory first
        base_path = Path(__file__).parent
        filepath = base_path / filename
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def render(self) -> None:
        """Render the wizard's content."""
        if self.rendered:
            return
        self._update_view()
        self.rendered = True

    def _get_data_from_node(self):
        """Try to extract bands and dos data from the AiiDA process node."""
        bands_data = None
        dos_data = None

        if self.model.has_process:
            outputs = self.model.process.outputs
            # Look for BandsData in outputs
            for label in outputs:
                node = outputs[label]
                if isinstance(node, BandsData):
                    # In a real scenario, you'd convert BandsData to the widget's JSON format
                    # For now, we return None to fall back to the demo JSONs
                    pass
        return bands_data, dos_data

    def _update_view(self):

        print("ResultsWizardStep __init__ model process uuid", self.model.process_uuid)
        print("has process", self.model.has_process)
        #if not self.model.has_process:
        if not self.model.process_uuid:
            self.children = [ipw.HTML("Waiting for calculation results...")]
            return

        data_node = load_node(self.model.process_uuid)
        #print("data_node", data_node)
        #print("data_node outputs", data_node.get_dict()) #.get("results"))
        
        #outputs = None #dict(self.model.outputs)

        # 1. Structure Panel
        structure_node = self.model.final_structure
        #structure_node = next((n for n in outputs.values() if isinstance(n, StructureData)), None)
        #if structure_node:
        structure_vwr = awb.viewers.StructureDataViewer(structure=structure_node)
        #else:
        #    structure_vwr = ipw.HTML("<p>No output structure found for this process.</p>")

        # 2. Phonon Dispersion Panel
        #bands_node = next((n for n in outputs.values() if isinstance(n, BandsData)), None)
        bands_node = None
        if bands_node:
            phonon_vwr = BandsDataViewer(bands_node, downloadable=True)
        else:
            # Fallback to demo data
            Bands = plugins.DataFactory("core.array.bands")
            bs = Bands()
            kpoints = np.array(
                [
                    [0.0, 0.0, 0.0],
                    [0.1, 0.0, 0.1],
                    [0.2, 0.0, 0.2],
                    [0.3, 0.0, 0.3],
                    [0.4, 0.0, 0.4],
                    [0.5, 0.0, 0.5],
                    [0.5, 0.0, 0.5],
                    [0.525, 0.05, 0.525],
                    [0.55, 0.1, 0.55],
                    [0.575, 0.15, 0.575],
                    [0.6, 0.2, 0.6],
                    [0.625, 0.25, 0.625],
                ]
            )
            bands = np.array(
                [
                    [-5.64024889, 6.66929678, 6.66929678, 6.66929678, 8.91047649],
                    [-5.46976726, 5.76113772, 5.97844699, 5.97844699, 8.48186734],
                    [-4.93870761, 4.06179965, 4.97235487, 4.97235488, 7.68276008],
                    [-4.05318686, 2.21579935, 4.18048674, 4.18048675, 7.04145185],
                    [-2.83974972, 0.37738276, 3.69024464, 3.69024465, 6.75053465],
                    [-1.34041116, -1.34041115, 3.52500177, 3.52500178, 6.92381041],
                    [-1.34041116, -1.34041115, 3.52500177, 3.52500178, 6.92381041],
                    [-1.34599146, -1.31663872, 3.34867603, 3.54390139, 6.93928289],
                    [-1.36769345, -1.24523403, 2.94149041, 3.6004033, 6.98809593],
                    [-1.42050683, -1.12604118, 2.48497007, 3.69389815, 7.07537154],
                    [-1.52788845, -0.95900776, 2.09104321, 3.82330632, 7.20537566],
                    [-1.71354964, -0.74425095, 1.82242466, 3.98697455, 7.37979746],
                ]
            )
            bs.set_kpoints(kpoints)
            bs.set_bands(bands)
            bs.labels = [(0, "GAMMA"), (5, "X"), (6, "Z"), (11, "U")]
            np.bool8 = np.bool
            phonon_vwr = BandsDataViewer(bs, downloadable=True)

        # Result tabs
        tabs = ipw.Tab(children=[structure_vwr, phonon_vwr])
        tabs.set_title(0, "Resulting Structure")
        tabs.set_title(1, "Phonon Dispersion")

        self.children = [
            ipw.HTML(f"<h4>Results for Process: {self.model.process_uuid}</h4>"),
            tabs,
        ]
        