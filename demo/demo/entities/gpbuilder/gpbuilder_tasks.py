from pathlib import Path
from typing import Dict, Any
import json

def build_structure(name: str, atoms: list, bonds: list, project_dir: Path) -> Dict[str, Any]:
    """Build molecular structure and save to project directory"""
    structure_file = project_dir / "outputs" / f"{name}_structure.json"
    
    structure_data = {
        "name": name,
        "atoms": atoms,
        "bonds": bonds,
        "num_atoms": len(atoms),
        "num_bonds": len(bonds)
    }
    
    structure_file.write_text(json.dumps(structure_data, indent=2))
    
    return {
        "structure_file": str(structure_file),
        "num_atoms": len(atoms),
        "num_bonds": len(bonds)
    }

def evaluate_energy(structure_file: str, method: str, project_dir: Path) -> Dict[str, Any]:
    """Evaluate energy of molecular structure"""
    # Load structure
    structure_path = Path(structure_file)
    if not structure_path.is_absolute():
        structure_path = project_dir / structure_path
    
    structure_data = json.loads(structure_path.read_text())
    
    # Simulate energy calculation
    energy = -100.5 + len(structure_data["atoms"]) * 0.1
    
    # Save results
    energy_file = project_dir / "outputs" / f"{structure_data['name']}_energy.json"
    energy_data = {
        "structure": structure_data["name"],
        "method": method,
        "energy": energy,
        "units": "kcal/mol"
    }
    
    energy_file.write_text(json.dumps(energy_data, indent=2))
    
    return {
        "energy": energy,
        "units": "kcal/mol",
        "energy_file": str(energy_file)
    }
