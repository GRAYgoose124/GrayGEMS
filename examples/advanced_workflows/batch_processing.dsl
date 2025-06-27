# Batch Processing Workflow
# This workflow demonstrates loops and parallel processing of multiple files

# Define variables
var input_files = "${input_files}"
var output_dir = "${output_dir}"
var batch_size = "${batch_size}"

# Step 1: Process each file in the batch
for file in input_files:
    # Process each file in parallel
    parallel:
        step validate_file: file_utils.validate(file=file)
        step backup_file: file_utils.copy(source=file, target="backup/")
    
    # Process based on validation result
    if validate_file.success:
        parallel:
            step process_file: data_processor.transform(input=file, output=output_dir)
            step analyze_file: data_processor.analyze(input=file)
        
        # Generate reports for processed file
        step report_file: text_processor.generate_report(data=analyze_file.result)
    else:
        step log_invalid: text_processor.log_error(message="Invalid file: " + file)

# Step 2: Aggregate results
step aggregate: data_processor.aggregate(input=output_dir, batch_size=batch_size)

# Step 3: Generate batch summary
step batch_summary: text_processor.generate_batch_summary(data=aggregate.result) 