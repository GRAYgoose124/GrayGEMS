# Conditional Workflow Example
# This workflow demonstrates complex conditional logic and branching

# Define variables
var data_type = "${data_type}"
var input_file = "${input_file}"
var processing_mode = "${processing_mode}"

# Step 1: Detect data type
step detect_type: data_processor.detect_type(file=input_file)

# Step 2: Process based on detected type
if data_type == "csv":
    step process_csv: data_processor.process_csv(input=input_file)
    
    if processing_mode == "fast":
        step quick_analysis: data_processor.quick_analysis(input=process_csv.result)
    else:
        step detailed_analysis: data_processor.detailed_analysis(input=process_csv.result)
        
elif data_type == "json":
    step process_json: data_processor.process_json(input=input_file)
    
    if processing_mode == "fast":
        step quick_analysis: data_processor.quick_analysis(input=process_json.result)
    else:
        step detailed_analysis: data_processor.detailed_analysis(input=process_json.result)
        
elif data_type == "xml":
    step process_xml: data_processor.process_xml(input=input_file)
    
    if processing_mode == "fast":
        step quick_analysis: data_processor.quick_analysis(input=process_xml.result)
    else:
        step detailed_analysis: data_processor.detailed_analysis(input=process_xml.result)
        
else:
    # Unknown data type - try generic processing
    step process_generic: data_processor.process_generic(input=input_file)
    step log_unknown: text_processor.log_warning(message="Unknown data type: " + data_type)

# Step 3: Generate appropriate output based on processing mode
if processing_mode == "fast":
    step generate_quick_report: text_processor.generate_quick_report(data=quick_analysis.result)
else:
    parallel:
        step generate_detailed_report: text_processor.generate_detailed_report(data=detailed_analysis.result)
        step generate_summary: text_processor.generate_summary(data=detailed_analysis.result)
        step export_results: data_processor.export(data=detailed_analysis.result, format="json") 