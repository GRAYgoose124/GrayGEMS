# Advanced Workflows in GrayGEMS

GrayGEMS now supports advanced workflow features including a Domain Specific Language (DSL), reusable templates, and sophisticated execution patterns with conditions, parallel execution, and loops.

## Table of Contents

- [DSL Overview](#dsl-overview)
- [DSL Syntax](#dsl-syntax)
- [Workflow Templates](#workflow-templates)
- [Advanced Execution Features](#advanced-execution-features)
- [CLI Usage](#cli-usage)
- [Examples](#examples)
- [API Reference](#api-reference)

## DSL Overview

The GrayGEMS DSL (Domain Specific Language) allows you to write workflows in a human-readable, pseudocode-like format that gets compiled into executable workflow definitions.

### Key Features

- **Human-readable syntax** - Write workflows like pseudocode
- **Variable declarations** - Define reusable variables
- **Service calls** - Execute tasks from registered services
- **Conditional logic** - Branch execution based on conditions
- **Parallel execution** - Run multiple steps concurrently
- **Loops** - Iterate over collections
- **Template support** - Reusable workflow patterns

## DSL Syntax

### Variables

Define variables that can be referenced throughout the workflow:

```dsl
var input_file = "data.csv"
var output_dir = "results"
var batch_size = 10
var files = ["file1.csv", "file2.csv"]
```

### Service Steps

Execute tasks from registered services:

```dsl
step validate: file_utils.validate(file=input_file)
step process: data_processor.transform(input=input_file, output=output_dir)
step report: text_processor.generate_report(data=process.result)
```

### Conditions

Execute different paths based on conditions:

```dsl
if validate.success:
    step backup: file_utils.copy(source=input_file, target="backup/")
    step analyze: data_processor.analyze(input=input_file)
else:
    step fix_data: data_processor.clean(input=input_file)
```

### Parallel Execution

Run multiple steps concurrently:

```dsl
parallel:
    step analyze: data_processor.analyze(input=input_file)
    step transform: data_processor.transform(input=input_file, output=output_dir)
    step backup: file_utils.copy(source=input_file, target="backup/")
```

### Loops

Iterate over collections:

```dsl
for file in files:
    step process: data_processor.transform(input=file, output=output_dir)
    step validate: file_utils.validate(file=file)
```

### Parameter Types

The DSL supports various parameter types:

```dsl
# Strings
step task1: service.task(message="Hello World")

# Numbers
step task2: service.task(count=42, ratio=0.5)

# Booleans
step task3: service.task(enabled=true, debug=false)

# Arrays
step task4: service.task(items=[1, 2, 3], files=["a.csv", "b.csv"])

# Objects
step task5: service.task(config={"key": "value", "nested": {"data": 123}})
```

## Workflow Templates

Templates provide reusable workflow patterns with parameterization.

### Built-in Templates

GrayGEMS comes with several built-in templates:

#### data_processing
A basic data processing workflow with validation and conditional processing.

**Parameters:**
- `input_file` - Input file path
- `output_dir` - Output directory
- `backup_dir` - Backup directory

#### parallel_processing
Process multiple files in parallel.

**Parameters:**
- `input_files` - List of input files
- `output_dir` - Output directory
- `backup_dir` - Backup directory

#### conditional_workflow
Workflow with conditional logic based on data type.

**Parameters:**
- `data_type` - Type of data (csv, json, xml)
- `input_file` - Input file path

### Creating Custom Templates

You can create your own templates:

```python
from graygems.core.workflow_dsl import WorkflowTemplate

dsl_code = """
var input_file = "${input_file}"
var output_dir = "${output_dir}"

step process: data_processor.transform(input=input_file, output=output_dir)
"""

template = WorkflowTemplate(
    name="my_template",
    dsl_code=dsl_code,
    parameters={"input_file": "default.csv", "output_dir": "default_results"}
)

# Register the template
from graygems.core.workflow_dsl import template_registry
template_registry.register(template)
```

## Advanced Execution Features

### Conditional Execution

Workflows can branch based on step results:

```dsl
step validate: file_utils.validate(file=input_file)

if validate.success:
    # Execute if validation succeeds
    step process: data_processor.transform(input=input_file)
else:
    # Execute if validation fails
    step fix: data_processor.clean(input=input_file)
```

### Parallel Execution

Multiple steps can run concurrently:

```dsl
parallel:
    step task1: service1.operation1()
    step task2: service2.operation2()
    step task3: service3.operation3()
```

### Loop Execution

Iterate over collections:

```dsl
var files = ["file1.csv", "file2.csv", "file3.csv"]

for file in files:
    step process: data_processor.transform(input=file)
    step validate: file_utils.validate(file=file)
```

### Dependency Resolution

Steps automatically resolve dependencies:

```dsl
step step1: service1.task1()
step step2: service2.task2(input=step1.result)  # Depends on step1
step step3: service3.task3(data=step2.output)   # Depends on step2
```

## CLI Usage

### List Templates

```bash
python -m graygems.cli list-templates
```

### Show Template Details

```bash
python -m graygems.cli show-template template_name
```

### Run DSL Workflow

```bash
python -m graygems.cli run-dsl project_id workflow.dsl -p param1 value1 -p param2 value2
```

### Run Template Workflow

```bash
python -m graygems.cli run-template project_id template_name -p param1 value1 -p param2 value2
```

### Compile DSL to JSON

```bash
python -m graygems.cli compile-dsl workflow.dsl -o workflow.json
```

### Create Template

```bash
python -m graygems.cli create-template template_name workflow.dsl -p param1 value1
```

## Examples

### Simple Data Processing

```dsl
# Simple data processing workflow
var input_file = "data.csv"
var output_dir = "results"

step validate: file_utils.validate(file=input_file)
step process: data_processor.transform(input=input_file, output=output_dir)
step report: text_processor.generate_report(data=process.result)
```

### Conditional Processing

```dsl
# Conditional data processing
var input_file = "data.csv"
var output_dir = "results"

step validate: file_utils.validate(file=input_file)

if validate.success:
    step backup: file_utils.copy(source=input_file, target="backup/")
    step process: data_processor.transform(input=input_file, output=output_dir)
    step analyze: data_processor.analyze(input=input_file)
else:
    step fix_data: data_processor.clean(input=input_file)
    step retry_validate: file_utils.validate(file=input_file)
```

### Parallel Processing

```dsl
# Parallel processing workflow
var input_file = "data.csv"
var output_dir = "results"

step validate: file_utils.validate(file=input_file)

if validate.success:
    parallel:
        step backup: file_utils.copy(source=input_file, target="backup/")
        step analyze: data_processor.analyze(input=input_file)
        step transform: data_processor.transform(input=input_file, output=output_dir)
    
    step report: text_processor.generate_report(data=analyze.result)
```

### Batch Processing

```dsl
# Batch processing with loops
var input_files = ["file1.csv", "file2.csv", "file3.csv"]
var output_dir = "results"

for file in input_files:
    step validate: file_utils.validate(file=file)
    
    if validate.success:
        step process: data_processor.transform(input=file, output=output_dir)
    else:
        step log_error: text_processor.log_error(message="Invalid file: " + file)

step aggregate: data_processor.aggregate(input=output_dir)
```

## API Reference

### WorkflowDSL

The main DSL parser class.

```python
from graygems.core.workflow_dsl import WorkflowDSL

dsl = WorkflowDSL()
workflow = dsl.parse_workflow(dsl_code)
```

### WorkflowTemplate

Template class for reusable workflows.

```python
from graygems.core.workflow_dsl import WorkflowTemplate

template = WorkflowTemplate(name, dsl_code, parameters)
workflow = template.compile(**runtime_params)
```

### WorkflowManager

Enhanced workflow manager with DSL support.

```python
from graygems.core.workflow import WorkflowManager

# Execute DSL workflow
result = await workflow_manager.execute_dsl_workflow(
    project_id, dsl_code, project_dir, **parameters
)

# Execute template workflow
result = await workflow_manager.execute_template_workflow(
    project_id, template_name, project_dir, **parameters
)
```

### Template Registry

Global registry for workflow templates.

```python
from graygems.core.workflow_dsl import template_registry

# List templates
templates = template_registry.list_templates()

# Get template
template = template_registry.get("template_name")

# Register template
template_registry.register(template)
```

## Best Practices

1. **Use meaningful variable names** - Make your DSL code self-documenting
2. **Group related steps** - Use parallel blocks for independent operations
3. **Handle errors gracefully** - Use conditional logic for error handling
4. **Create reusable templates** - Extract common patterns into templates
5. **Test your workflows** - Use the test suite to validate workflow logic
6. **Document complex workflows** - Add comments to explain business logic

## Migration from JSON

If you have existing JSON workflows, you can gradually migrate to DSL:

1. **Start with simple workflows** - Convert basic sequential workflows first
2. **Use the compiler** - Use `compile-dsl` to convert DSL to JSON for comparison
3. **Test thoroughly** - Ensure DSL workflows produce the same results
4. **Leverage templates** - Extract common patterns into reusable templates

The DSL provides a more maintainable and readable way to define workflows while maintaining full compatibility with the existing JSON format. 