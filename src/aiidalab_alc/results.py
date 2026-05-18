"""Module for defining widgets/models for viewing process progress and results."""

import json
from pathlib import Path
from typing import cast
import numpy as np

import aiidalab_widgets_base as awb
from aiida import plugins
from aiida.orm import BandsData
import ipywidgets as ipw
import traitlets as tl
from aiida.common.exceptions import NotExistent
from aiida.orm import BandsData, NodeLinksManager, ProcessNode, XyData, load_node
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
        """Return the outputs for teh process."""
        return self.process.outputs if self.has_process else []


class ResultsModel(ProcessModel):
    """MVC results step model."""

    blocked = tl.Bool(False)


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
        BandsData = plugins.DataFactory("core.array.bands")
        bs = BandsData()
        kpoints = np.array(
        [
        [0.0, 0.0, 0.0],  # array shape is 12 * 3
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
        [
            -5.64024889,
            6.66929678,
            6.66929678,
            6.66929678,
            8.91047649,
        ],  # array shape is 12 * 5, where 12 is the size of the kpoints mesh
        [
            -5.46976726,
            5.76113772,
            5.97844699,
            5.97844699,
            8.48186734,
        ],  # and 5 is the number of states
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
        labels = [(0, "GAMMA"), (5, "X"), (6, "Z"), (11, "U")]
        bs.labels = labels


        vwr = BandsDataViewer(bs.store(), downloadable=True)
        display(vwr)
        self.children = [
                ipw.HTML(f"<h3>Results for Process: {self.model.process_uuid}</h3>"),
                vwr
            ]
        