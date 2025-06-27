from typing import List
from pydantic import BaseModel

from graygems.core.service import Service
from graygems.core.registry import global_registry

from .gpbuilder_tasks import build_structure, evaluate_energy

# Input/Output models
class BuildStructureInput(BaseModel):
    name: str
    atoms: List[dict]
    bonds: List[dict]

class BuildStructureOutput(BaseModel):
    structure_file: str
    num_atoms: int
    num_bonds: int

class EvaluateEnergyInput(BaseModel):
    structure_file: str
    method: str = "PM3"

class EvaluateEnergyOutput(BaseModel):
    energy: float
    units: str
    energy_file: str

# Service implementations
class BuildStructureService(Service[BuildStructureInput, BuildStructureOutput]):
    def __init__(self):
        super().__init__(
            input_model=BuildStructureInput,
            output_model=BuildStructureOutput,
            task_func=build_structure
        )

class EvaluateEnergyService(Service[EvaluateEnergyInput, EvaluateEnergyOutput]):
    def __init__(self):
        super().__init__(
            input_model=EvaluateEnergyInput,
            output_model=EvaluateEnergyOutput,
            task_func=evaluate_energy,
            dependencies=["structure"]  # Depends on structure being built first
        )

class GpBuilder:
    """Entity grouping molecular modeling services"""
    
    def __init__(self):
        self.registry = global_registry
        self._register_services()
    
    def _register_services(self):
        """Register all GpBuilder services"""
        self.registry.register("gpbuilder.build", BuildStructureService())
        self.registry.register("gpbuilder.evaluate", EvaluateEnergyService())
