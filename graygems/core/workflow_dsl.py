"""
GrayGEMS Workflow DSL (Domain Specific Language)
Provides a pseudocode language for defining workflows with conditions, branching, and parallel execution.
"""

import re
import json
import logging
import ast
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class StepType(Enum):
    """Types of workflow steps"""

    SERVICE = "service"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SEQUENCE = "sequence"
    LOOP = "loop"
    VARIABLE = "variable"


@dataclass
class DSLStep:
    """Represents a step in the DSL workflow"""

    step_id: str
    step_type: StepType
    content: Dict[str, Any]
    dependencies: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.metadata is None:
            self.metadata = {}


class WorkflowDSL:
    """DSL parser for workflow definitions"""

    def __init__(self):
        self.step_counter = 0
        self.loop_counter = 0
        self.condition_counter = 0
        self.parallel_counter = 0
        self.parsed_blocks = {}  # Track parsed blocks to avoid duplicates

    def _parse_variable(self, line: str) -> Tuple[str, Any]:
        """Parse a variable declaration"""
        # Remove 'var ' prefix and split on '='
        var_part = line[4:].strip()
        if '=' not in var_part:
            raise ValueError(f"Invalid variable declaration: {line}")
        
        var_name, var_value = var_part.split('=', 1)
        var_name = var_name.strip()
        var_value = var_value.strip()
        
        # Try to parse the value
        try:
            # Try to evaluate as Python literal
            parsed_value = ast.literal_eval(var_value)
            return var_name, parsed_value
        except (ValueError, SyntaxError):
            # If it's not a valid Python literal, treat as string
            return var_name, var_value

    def _parse_parameters(self, param_str: str, known_steps: set = None) -> Dict[str, Any]:
        """Parse function parameters with proper handling of complex values, and convert step.field references to $step.field if step is known."""
        if not param_str.strip():
            return {}
        
        params = {}
        # Split by comma, but handle nested parentheses, brackets, and quotes
        param_parts = self._split_params(param_str)
        
        for part in param_parts:
            part = part.strip()
            if '=' in part:
                key, value_str = part.split('=', 1)
                key = key.strip()
                value_str = value_str.strip()
                
                # Try to parse the value
                try:
                    # Try to evaluate as Python literal first
                    value = ast.literal_eval(value_str)
                except (ValueError, SyntaxError):
                    # If it's not a valid Python literal, treat as string
                    # Remove quotes if present
                    if (value_str.startswith('"') and value_str.endswith('"')) or \
                       (value_str.startswith("'") and value_str.endswith("'")):
                        value = value_str[1:-1]
                    else:
                        value = value_str
                
                # If value is a string, check for various patterns that need resolution
                if isinstance(value, str):
                    # Check for step.field references and convert to $step.field if step is known
                    if (
                        known_steps is not None
                        and re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_\.]*)$", value)
                    ):
                        step_candidate = value.split(".")[0]
                        if step_candidate in known_steps:
                            value = f"${value}"
                    
                    # Check for string concatenation expressions (e.g., "Invalid file: " + file)
                    elif "+" in value and re.search(r'["\'][^"\']*["\'][^+]*\+[^+]*[a-zA-Z_][a-zA-Z0-9_]*', value):
                        # This looks like string concatenation, mark it for later evaluation
                        value = f"EVAL:{value}"
                
                params[key] = value
        
        return params

    def _split_params(self, params_str: str) -> List[str]:
        """Split parameters by comma, respecting parentheses, brackets, and quotes"""
        params = []
        current = ""
        paren_count = 0
        bracket_count = 0
        quote_char = None
        
        for char in params_str:
            if char in ['"', "'"] and (quote_char is None or char == quote_char):
                if quote_char is None:
                    quote_char = char
                else:
                    quote_char = None
                current += char
            elif quote_char is not None:
                # Inside quotes, add all characters
                current += char
            elif char == "(":
                paren_count += 1
                current += char
            elif char == ")":
                paren_count -= 1
                current += char
            elif char == "[":
                bracket_count += 1
                current += char
            elif char == "]":
                bracket_count -= 1
                current += char
            elif char == "," and paren_count == 0 and bracket_count == 0:
                params.append(current.strip())
                current = ""
                continue
            else:
                current += char
        
        if current.strip():
            params.append(current.strip())
        
        return params

    def _parse_service_step(self, line: str, known_steps: set = None) -> Tuple[str, Dict[str, Any]]:
        """Parse a service step declaration, passing known_steps for reference resolution."""
        # Extract step name and service call
        step_match = re.match(r"step\s+(\w+):\s*(\w+)\.(\w+)\((.*)\)", line)
        if not step_match:
            raise ValueError(f"Invalid service step: {line}")
        
        step_id = step_match.group(1)
        service = step_match.group(2)
        task = step_match.group(3)
        params_str = step_match.group(4)
        
        inputs = self._parse_parameters(params_str, known_steps=known_steps)
        
        step_config = {
            "service": service,
            "task": task,
            "inputs": inputs,
            "dependencies": [],
            "type": "service"
        }
        
        return step_id, step_config

    def _extract_block(self, lines: List[str], start_idx: int) -> Tuple[List[str], int]:
        """Extract a block of indented lines starting from start_idx"""
        block_lines = []
        i = start_idx + 1
        
        # Find the indentation level of the block header
        header_line = lines[start_idx]
        header_indent = len(header_line) - len(header_line.lstrip())
        
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith("#"):
                i += 1
                continue
            
            # Determine indentation level
            indent = len(line) - len(line.lstrip())
            
            # If this line is at the same or less indentation as the header, 
            # and it's not empty, it's the end of the block
            if indent <= header_indent and stripped:
                # Check if it's a new top-level construct
                if (stripped.startswith("step ") or stripped.startswith("if ") or 
                    stripped == "parallel:" or stripped.startswith("for ") or
                    stripped.startswith("var ")):
                    break
            
            # This line is part of the block
            block_lines.append(line)
            i += 1
        
        return block_lines, i

    def _get_block_key(self, block_type: str, content: str) -> str:
        """Generate a unique key for a block to avoid duplicates"""
        return f"{block_type}:{hash(content)}"

    def _parse_workflow_recursive(self, lines: List[str], start_idx: int = 0, known_steps: set = None) -> Tuple[Dict[str, Any], List[str], int]:
        """Recursive workflow parser that tracks known step names for reference resolution."""
        if known_steps is None:
            known_steps = set()
        steps = {}
        top_level_ids = []
        i = start_idx
        while i < len(lines):
            line = lines[i]
            stripped = line.lstrip()
            if stripped.startswith("step "):
                step_id, step_config = self._parse_service_step(stripped, known_steps=known_steps)
                steps[step_id] = step_config
                top_level_ids.append(step_id)
                known_steps.add(step_id)
                i += 1
            elif stripped.startswith("for "):
                loop_steps, loop_ids, next_idx = self._parse_loop_recursive(lines, i, known_steps=known_steps)
                steps.update(loop_steps)
                top_level_ids.extend(loop_ids)
                i = next_idx
            elif stripped.startswith("if "):
                cond_steps, cond_ids, next_idx = self._parse_condition_recursive(lines, i, known_steps=known_steps)
                steps.update(cond_steps)
                top_level_ids.extend(cond_ids)
                i = next_idx
            elif stripped == "parallel:":
                parallel_steps, parallel_ids, next_idx = self._parse_parallel_recursive(lines, i, known_steps=known_steps)
                steps.update(parallel_steps)
                top_level_ids.extend(parallel_ids)
                i = next_idx
            else:
                i += 1
        return steps, top_level_ids, i

    def _parse_loop_recursive(self, lines: List[str], start_idx: int, known_steps: set = None) -> Tuple[Dict[str, Any], List[str], int]:
        """Parse a loop block recursively, passing known_steps for reference resolution."""
        loop_line = lines[start_idx]
        loop_match = re.match(r"for\s+(\w+)\s+in\s+(.+)", loop_line.lstrip())
        if not loop_match:
            raise ValueError(f"Invalid loop: {loop_line}")
        var_name = loop_match.group(1)
        collection = loop_match.group(2).strip()
        if collection.endswith(":"):
            collection = collection[:-1].strip()
        block_lines, next_idx = self._extract_block(lines, start_idx)
        # Recursively parse the loop body
        body_steps, body_ids, _ = self._parse_workflow_recursive(block_lines, 0, known_steps=known_steps.copy())
        loop_step_id = f"loop_{self.loop_counter}"
        self.loop_counter += 1
        loop_config = {
            "type": "loop",
            "variable": var_name,
            "collection": collection,
            "steps": body_ids,
            "dependencies": [],
        }
        all_steps = {loop_step_id: loop_config}
        all_steps.update(body_steps)
        return all_steps, [loop_step_id], next_idx

    def _parse_condition_recursive(self, lines: List[str], start_idx: int, known_steps: set = None) -> Tuple[Dict[str, Any], List[str], int]:
        """Parse a condition block recursively, passing known_steps for reference resolution."""
        condition_line = lines[start_idx]
        condition_match = re.match(r"if\s+(.+):", condition_line.lstrip())
        if not condition_match:
            raise ValueError(f"Invalid condition: {condition_line}")
        condition = condition_match.group(1).strip()
        if condition.endswith(":"):
            condition = condition[:-1].strip()
        block_lines, next_idx = self._extract_block(lines, start_idx)
        else_pos = -1
        for i, line in enumerate(block_lines):
            if line.lstrip() == "else:":
                else_pos = i
                break
        if_section_lines = block_lines[:else_pos] if else_pos != -1 else block_lines
        if_steps, if_ids, _ = self._parse_workflow_recursive(if_section_lines, 0, known_steps=known_steps.copy())
        else_steps, else_ids = {}, []
        if else_pos != -1:
            else_section_lines = block_lines[else_pos + 1:]
            else_steps, else_ids, _ = self._parse_workflow_recursive(else_section_lines, 0, known_steps=known_steps.copy())
        condition_step_id = f"condition_{self.condition_counter}"
        self.condition_counter += 1
        condition_config = {
            "type": "condition",
            "condition": condition,
            "if_steps": if_ids,
            "else_steps": else_ids,
            "dependencies": [],
        }
        all_steps = {condition_step_id: condition_config}
        all_steps.update(if_steps)
        all_steps.update(else_steps)
        return all_steps, [condition_step_id], next_idx

    def _parse_parallel_recursive(self, lines: List[str], start_idx: int, known_steps: set = None) -> Tuple[Dict[str, Any], List[str], int]:
        """Parse a parallel block recursively, passing known_steps for reference resolution."""
        block_lines, next_idx = self._extract_block(lines, start_idx)
        body_steps, body_ids, _ = self._parse_workflow_recursive(block_lines, 0, known_steps=known_steps.copy())
        parallel_step_id = f"parallel_{self.parallel_counter}"
        self.parallel_counter += 1
        parallel_config = {
            "type": "parallel",
            "steps": body_ids,
            "dependencies": [],
        }
        all_steps = {parallel_step_id: parallel_config}
        all_steps.update(body_steps)
        return all_steps, [parallel_step_id], next_idx

    def _calculate_dependencies(self, steps: Dict[str, Any]) -> Dict[str, List[str]]:
        """Calculate dependencies between steps based on input references"""
        dependencies = {}
        
        for step_id, step_config in steps.items():
            if step_config.get("type") != "service":
                dependencies[step_id] = []
                continue
                
            deps = []
            inputs = step_config.get("inputs", {})
            
            for input_value in inputs.values():
                # Look for references to other step results
                if isinstance(input_value, str):
                    # Handle both formats: step.field and $step.field
                    if input_value.startswith("$"):
                        # Remove $ prefix and check for step.field pattern
                        ref_value = input_value[1:]
                        if "." in ref_value:
                            ref_step = ref_value.split(".")[0]
                            if ref_step in steps:
                                deps.append(ref_step)
                    elif "." in input_value:
                        # Original format: step.field
                        ref_step = input_value.split(".")[0]
                        if ref_step in steps:
                            deps.append(ref_step)
            
            dependencies[step_id] = deps
        
        return dependencies

    def parse_workflow(self, dsl_code: str) -> Dict[str, Any]:
        """Parse a complete workflow DSL, using known_steps for reference resolution."""
        self.step_counter = 0
        self.loop_counter = 0
        self.condition_counter = 0
        self.parallel_counter = 0
        self.parsed_blocks = {}
        lines = []
        for line in dsl_code.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(line)
        
        # First pass: collect all step names
        all_step_names = set()
        for line in lines:
            if line.lstrip().startswith("step ") and ":" in line:
                step_name = line.lstrip().split(":", 1)[0].replace("step ", "").strip()
                all_step_names.add(step_name)
        
        # Second pass: parse variables and workflow
        variables = {}
        workflow_lines = []
        for line in lines:
            if line.lstrip().startswith("var "):
                var_name, var_value = self._parse_variable(line.lstrip())
                variables[var_name] = var_value
            else:
                workflow_lines.append(line)
        
        # Parse workflow with full step knowledge
        steps, _, _ = self._parse_workflow_recursive(workflow_lines, 0, known_steps=all_step_names)
        dependencies = self._calculate_dependencies(steps)
        for step_id, deps in dependencies.items():
            if step_id in steps:
                steps[step_id]["dependencies"] = deps
        workflow = {
            "steps": steps,
            "variables": variables,
            "metadata": {"source": dsl_code, "compiled_at": "2024-01-01T00:00:00Z"},
        }
        return workflow


class WorkflowTemplate:
    """Reusable workflow template with parameterization"""

    def __init__(self, name: str, dsl_code: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.dsl_code = dsl_code
        self.parameters = parameters or {}
        self.compiled_workflow = None

    def compile(self, **kwargs) -> Dict[str, Any]:
        """Compile the template with provided parameters"""
        compiled_dsl = self.dsl_code
        all_params = self.parameters.copy()
        all_params.update(kwargs)

        print("DEBUG - Parameters for substitution:")
        for param_name, param_value in all_params.items():
            print(f"  {param_name}: {param_value} (type: {type(param_value)})")

        for param_name, param_value in all_params.items():
            placeholder = f"${{{param_name}}}"

            # Handle unquoted placeholders in var assignments: var name = ${param}
            unquoted_pattern = re.compile(
                rf"(var\s+{param_name}\s*=\s*){re.escape(placeholder)}"
            )
            if isinstance(param_value, str):
                unquoted_replacement = f'"{param_value}"'
            else:
                unquoted_replacement = str(param_value)
            compiled_dsl = unquoted_pattern.sub(
                rf"\1{unquoted_replacement}", compiled_dsl
            )

            # Handle quoted placeholders in var assignments: var name = "${param}"
            quoted_pattern = re.compile(
                rf'(var\s+{param_name}\s*=\s*)["\"][^"\"]*{re.escape(placeholder)}[^"\"]*["\"]'
            )
            if isinstance(param_value, str):
                quoted_replacement = f'"{param_value}"'
            else:
                quoted_replacement = str(param_value)
            compiled_dsl = quoted_pattern.sub(rf"\1{quoted_replacement}", compiled_dsl)

            # Handle placeholders in variable values: var name = ${param}
            var_pattern = re.compile(
                rf"(var\s+\w+\s*=\s*){re.escape(placeholder)}"
            )
            if isinstance(param_value, str):
                var_replacement = f'"{param_value}"'
            else:
                var_replacement = str(param_value)
            compiled_dsl = var_pattern.sub(rf"\1{var_replacement}", compiled_dsl)

            # Replace any remaining placeholders (not in var assignment)
            if isinstance(param_value, str):
                replacement = f'"{param_value}"'
            else:
                replacement = str(param_value)
            compiled_dsl = compiled_dsl.replace(placeholder, replacement)

        print("DEBUG - After substitution:")
        print(compiled_dsl)

        dsl_parser = WorkflowDSL()
        self.compiled_workflow = dsl_parser.parse_workflow(compiled_dsl)
        return self.compiled_workflow

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary"""
        return {
            "name": self.name,
            "dsl_code": self.dsl_code,
            "parameters": self.parameters,
            "compiled_workflow": self.compiled_workflow,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowTemplate":
        """Create template from dictionary"""
        template = cls(
            name=data["name"],
            dsl_code=data["dsl_code"],
            parameters=data.get("parameters", {}),
        )
        template.compiled_workflow = data.get("compiled_workflow")
        return template


class WorkflowTemplateRegistry:
    """Registry for workflow templates"""

    def __init__(self):
        self.templates: Dict[str, WorkflowTemplate] = {}

    def register(self, template: WorkflowTemplate):
        """Register a workflow template"""
        self.templates[template.name] = template

    def get(self, name: str) -> Optional[WorkflowTemplate]:
        """Get a template by name"""
        return self.templates.get(name)

    def list_templates(self) -> List[str]:
        """List all template names"""
        return list(self.templates.keys())

    def save_templates(self, file_path: Path):
        """Save templates to file"""
        data = {name: template.to_dict() for name, template in self.templates.items()}

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def load_templates(self, file_path: Path):
        """Load templates from file"""
        if not file_path.exists():
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        for name, template_data in data.items():
            template = WorkflowTemplate.from_dict(template_data)
            self.templates[name] = template


# Built-in workflow templates
BUILTIN_TEMPLATES = {
    "data_processing": WorkflowTemplate(
        name="data_processing",
        dsl_code="""
# Data processing workflow template
var input_file = "${input_file}"
var output_dir = "${output_dir}"

step validate: file_utils.validate(file=input_file)
step process: data_processor.transform(input=input_file, output=output_dir)

if validate.success:
    step backup: file_utils.copy(source=input_file, target="${backup_dir}/")
    step analyze: data_processor.analyze(input=input_file)
else:
    step fix_data: data_processor.clean(input=input_file)
""",
        parameters={
            "input_file": "data.csv",
            "output_dir": "results",
            "backup_dir": "backup",
        },
    ),
    "parallel_processing": WorkflowTemplate(
        name="parallel_processing",
        dsl_code="""
# Parallel processing workflow
var input_files = "${input_files}"

for file in input_files:
    parallel:
        step validate: file_utils.validate(file=file)
        step process: data_processor.transform(input=file, output="${output_dir}")
        step backup: file_utils.copy(source=file, target="${backup_dir}/")
""",
        parameters={
            "input_files": ["file1.csv", "file2.csv"],
            "output_dir": "results",
            "backup_dir": "backup",
        },
    ),
    "conditional_workflow": WorkflowTemplate(
        name="conditional_workflow",
        dsl_code="""
# Conditional workflow based on data type
var data_type = "${data_type}"
var input_file = "${input_file}"

step check_type: data_processor.detect_type(file=input_file)

if data_type == "csv":
    step process_csv: data_processor.process_csv(input=input_file)
elif data_type == "json":
    step process_json: data_processor.process_json(input=input_file)
else:
    step process_generic: data_processor.process_generic(input=input_file)
""",
        parameters={"data_type": "csv", "input_file": "data.csv"},
    ),
}

# Global template registry
template_registry = WorkflowTemplateRegistry()

# Register built-in templates
for template in BUILTIN_TEMPLATES.values():
    template_registry.register(template)
