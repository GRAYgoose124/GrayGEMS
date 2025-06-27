# Advanced Data Processing Workflow
# This workflow demonstrates conditions, parallel execution, and loops

# Define variables
var input_file = "${input_file}"
var output_dir = "${output_dir}"
var backup_dir = "${backup_dir}"

# Step 1: Validate input file
step validate: file_utils.validate(file=input_file)

# Step 2: Process data based on validation result
if validate.success:
    # If validation succeeds, run parallel processing
    step backup: file_utils.copy(source=input_file, target=backup_dir)
    
    parallel:
        step analyze: data_processor.analyze(input=input_file)
        step transform: data_processor.transform(input=input_file, output=output_dir)
        step report: text_processor.generate_report(data=input_file)
    
    # Step 3: Process results in parallel
    parallel:
        step summary: text_processor.generate_summary(data=analyze.result)
        step export: data_processor.export(data=transform.result, format="json")
else:
    # If validation fails, clean and retry
    step fix_data: data_processor.clean(input=input_file)
    step retry_validate: file_utils.validate(file=input_file)
    
    if retry_validate.success:
        step process_fixed: data_processor.transform(input=input_file, output=output_dir)
    else:
        step log_error: text_processor.log_error(message="Data validation failed after cleaning")

# Step 4: Final processing
step finalize: data_processor.finalize(input=output_dir) 