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
    """DSL parser and compiler for workflow definitions"""
    
    def __init__(self):
        self.step_counter = 0
        self.variables = {}
    
    def parse_workflow(self, dsl_code: str) -> Dict[str, Any]:
        """
        Parse DSL code and return a compiled workflow definition
        
        Example DSL:
        ```
        # Define variables
        var input_file = "data.csv"
        var output_dir = "results"
        
        # Service calls
        step validate_data: file_utils.validate(file=input_file)
        step process_data: data_processor.transform(input=input_file, output=output_dir)
        
        # Conditions
        if validate_data.success:
            step backup: file_utils.copy(source=input_file, target="backup/")
            step analyze: data_processor.analyze(input=input_file)
        else:
            step fix_data: data_processor.clean(input=input_file)
        
        # Parallel execution
        parallel:
            step report1: text_processor.generate_report(data=analyze.result)
            step report2: text_processor.generate_summary(data=analyze.result)
        
        # Loops
        for item in process_data.items:
            step process_item: data_processor.process_single(item=item)
        ```
        """
        lines = [line.strip() for line in dsl_code.split('\n') if line.strip() and not line.startswith('#')]
        
        workflow = {
            "steps": {},
            "variables": {},
            "metadata": {
                "source": dsl_code,
                "compiled_at": "2024-01-01T00:00:00Z"
            }
        }
        
        current_context = "root"
        context_stack = []
        
        for line in lines:
            if line.startswith("var "):
                # Variable declaration
                var_name, var_value = self._parse_variable(line)
                workflow["variables"][var_name] = var_value
                
            elif line.startswith("step "):
                # Service step
                step_id, step_config = self._parse_service_step(line)
                workflow["steps"][step_id] = step_config
                
            elif line.startswith("if "):
                # Condition block
                condition, condition_steps = self._parse_condition(lines, lines.index(line))
                workflow["steps"].update(condition_steps)
                
            elif line.startswith("parallel:"):
                # Parallel block
                parallel_steps = self._parse_parallel_block(lines, lines.index(line))
                workflow["steps"].update(parallel_steps)
                
            elif line.startswith("for "):
                # Loop block
                loop_steps = self._parse_loop_block(lines, lines.index(line))
                workflow["steps"].update(loop_steps)
        
        return workflow
    
    def _parse_variable(self, line: str) -> Tuple[str, Any]:
        """Parse variable declaration: var name = value"""
        match = re.match(r'var\s+(\w+)\s*=\s*(.+)', line)
        if not match:
            raise ValueError(f"Invalid variable declaration: {line}")
        
        var_name = match.group(1)
        var_value_str = match.group(2).strip()
        
        # If quoted string, treat as string
        if (var_value_str.startswith('"') and var_value_str.endswith('"')) or (var_value_str.startswith("'") and var_value_str.endswith("'")):
            var_value = var_value_str[1:-1]
        else:
            # Try to parse as Python literal (list, dict, int, float, bool, etc.)
            try:
                var_value = ast.literal_eval(var_value_str)
            except Exception:
                var_value = var_value_str
        
        print(f"[DEBUG] Parsed variable: {var_name} = {var_value_str} -> {var_value} (type: {type(var_value)})")
        return var_name, var_value
    
    def _parse_service_step(self, line: str) -> Tuple[str, Dict[str, Any]]:
        """Parse service step: step name: service.task(params)"""
        match = re.match(r'step\s+(\w+):\s*(\w+)\.(\w+)\((.+)\)', line)
        if not match:
            raise ValueError(f"Invalid service step: {line}")
        
        step_id = match.group(1)
        service_name = match.group(2)
        task_name = match.group(3)
        params_str = match.group(4)
        
        # Parse parameters
        inputs = self._parse_parameters(params_str)
        
        step_config = {
            "service": service_name,
            "task": task_name,
            "inputs": inputs,
            "dependencies": [],
            "type": "service"
        }
        
        return step_id, step_config
    
    def _parse_parameters(self, params_str: str) -> Dict[str, Any]:
        """Parse function parameters: key=value, key2=value2"""
        if not params_str.strip():
            return {}
        
        inputs = {}
        # Split by comma, but handle nested parentheses
        params = self._split_params(params_str)
        
        for param in params:
            if '=' in param:
                key, value_str = param.split('=', 1)
                key = key.strip()
                value_str = value_str.strip()
                
                # Try to parse as Python literal first (for lists, tuples, etc.)
                try:
                    # Handle both quoted and unquoted values
                    if value_str.startswith('"') and value_str.endswith('"'):
                        # Quoted string
                        value = value_str[1:-1]
                    elif value_str.startswith("'") and value_str.endswith("'"):
                        # Single quoted string
                        value = value_str[1:-1]
                    else:
                        # Try to parse as Python literal (for numbers, booleans, arrays, objects)
                        value = ast.literal_eval(value_str)
                except (ValueError, SyntaxError):
                    # If literal_eval fails, try JSON parsing
                    try:
                        value = json.loads(value_str)
                    except json.JSONDecodeError:
                        # If JSON parsing fails, treat as string
                        value = value_str
                
                inputs[key] = value
        
        return inputs
    
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
            elif char == '(':
                paren_count += 1
                current += char
            elif char == ')':
                paren_count -= 1
                current += char
            elif char == '[':
                bracket_count += 1
                current += char
            elif char == ']':
                bracket_count -= 1
                current += char
            elif char == ',' and paren_count == 0 and bracket_count == 0:
                params.append(current.strip())
                current = ""
                continue
            else:
                current += char
        
        if current.strip():
            params.append(current.strip())
        
        return params
    
    def _parse_condition(self, lines: List[str], start_idx: int) -> Tuple[str, Dict[str, Any]]:
        """Parse if-else condition block"""
        condition_line = lines[start_idx]
        condition_match = re.match(r'if\s+(.+)', condition_line)
        if not condition_match:
            raise ValueError(f"Invalid condition: {condition_line}")
        
        condition = condition_match.group(1).strip()
        
        # Find the block content
        block_lines = []
        else_block_lines = []
        in_else = False
        brace_count = 0
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            
            if line.startswith("else:"):
                in_else = True
                continue
            
            if line.startswith("if ") or line.startswith("parallel:") or line.startswith("for "):
                break
            
            if in_else:
                else_block_lines.append(line)
            else:
                block_lines.append(line)
        
        # Parse the blocks
        if_steps = self._parse_block_steps(block_lines)
        else_steps = self._parse_block_steps(else_block_lines) if else_block_lines else {}
        
        # Create condition step
        condition_step_id = f"condition_{self.step_counter}"
        self.step_counter += 1
        
        condition_config = {
            "type": "condition",
            "condition": condition,
            "if_steps": list(if_steps.keys()),
            "else_steps": list(else_steps.keys()),
            "dependencies": []
        }
        
        all_steps = {condition_step_id: condition_config}
        all_steps.update(if_steps)
        all_steps.update(else_steps)
        
        return condition, all_steps
    
    def _parse_parallel_block(self, lines: List[str], start_idx: int) -> Dict[str, Any]:
        """Parse parallel execution block"""
        block_lines = []
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            
            if line.startswith("if ") or line.startswith("parallel:") or line.startswith("for "):
                break
            
            block_lines.append(line)
        
        # Parse steps in the block
        steps = self._parse_block_steps(block_lines)
        
        # Create parallel step
        parallel_step_id = f"parallel_{self.step_counter}"
        self.step_counter += 1
        
        parallel_config = {
            "type": "parallel",
            "steps": list(steps.keys()),
            "dependencies": []
        }
        
        all_steps = {parallel_step_id: parallel_config}
        all_steps.update(steps)
        
        return all_steps
    
    def _parse_loop_block(self, lines: List[str], start_idx: int) -> Dict[str, Any]:
        """Parse for loop block"""
        loop_line = lines[start_idx]
        loop_match = re.match(r'for\s+(\w+)\s+in\s+(.+)', loop_line)
        if not loop_match:
            raise ValueError(f"Invalid loop: {loop_line}")
        
        var_name = loop_match.group(1)
        collection = loop_match.group(2).strip()
        # Fix: Remove trailing colon if present
        if collection.endswith(":"):
            collection = collection[:-1].strip()
        
        # Find the block content
        block_lines = []
        
        for i in range(start_idx + 1, len(lines)):
            line = lines[i]
            
            if line.startswith("if ") or line.startswith("parallel:") or line.startswith("for "):
                break
            
            block_lines.append(line)
        
        # Parse steps in the block
        steps = self._parse_block_steps(block_lines)
        
        # Create loop step
        loop_step_id = f"loop_{self.step_counter}"
        self.step_counter += 1
        
        loop_config = {
            "type": "loop",
            "variable": var_name,
            "collection": collection,
            "steps": list(steps.keys()),
            "dependencies": []
        }
        
        all_steps = {loop_step_id: loop_config}
        all_steps.update(steps)
        
        return all_steps
    
    def _parse_block_steps(self, lines: List[str]) -> Dict[str, Any]:
        """Parse steps within a block (if, parallel, loop)"""
        steps = {}
        
        for line in lines:
            if line.startswith("step "):
                step_id, step_config = self._parse_service_step(line)
                steps[step_id] = step_config
        
        return steps

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
            unquoted_pattern = re.compile(rf'(var\s+{param_name}\s*=\s*){re.escape(placeholder)}')
            if isinstance(param_value, str):
                unquoted_replacement = f'"{param_value}"'
            else:
                unquoted_replacement = str(param_value)
            compiled_dsl = unquoted_pattern.sub(rf'\1{unquoted_replacement}', compiled_dsl)
            
            # Handle quoted placeholders in var assignments: var name = "${param}"
            quoted_pattern = re.compile(rf'(var\s+{param_name}\s*=\s*)["\"][^"\"]*{re.escape(placeholder)}[^"\"]*["\"]')
            if isinstance(param_value, str):
                quoted_replacement = f'"{param_value}"'
            else:
                quoted_replacement = str(param_value)
            compiled_dsl = quoted_pattern.sub(rf'\1{quoted_replacement}', compiled_dsl)
            
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
            "compiled_workflow": self.compiled_workflow
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowTemplate':
        """Create template from dictionary"""
        template = cls(
            name=data["name"],
            dsl_code=data["dsl_code"],
            parameters=data.get("parameters", {})
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
        data = {
            name: template.to_dict()
            for name, template in self.templates.items()
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_templates(self, file_path: Path):
        """Load templates from file"""
        if not file_path.exists():
            return
        
        with open(file_path, 'r') as f:
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
            "backup_dir": "backup"
        }
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
            "backup_dir": "backup"
        }
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
        parameters={
            "data_type": "csv",
            "input_file": "data.csv"
        }
    )
}

# Global template registry
template_registry = WorkflowTemplateRegistry()

# Register built-in templates
for template in BUILTIN_TEMPLATES.values():
    template_registry.register(template) 