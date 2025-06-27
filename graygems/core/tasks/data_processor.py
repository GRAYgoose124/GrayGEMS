from typing import Dict, Any, List
from ..models import DataProcessorInput, DataProcessorOutput

def process_data(inputs: DataProcessorInput, project_dir: str = None) -> DataProcessorOutput:
    """Process data operations"""
    operation = inputs.operation
    data = inputs.data
    parameters = inputs.parameters or {}
    
    if operation == "filter":
        return _filter_data(data, parameters)
    elif operation == "sort":
        return _sort_data(data, parameters)
    elif operation == "aggregate":
        return _aggregate_data(data, parameters)
    elif operation == "transform":
        return _transform_data(data, parameters)
    else:
        return DataProcessorOutput(
            success=False,
            processed_data={},
            statistics={"error": f"Unknown operation: {operation}"}
        )

def _filter_data(data: Dict[str, Any], parameters: Dict[str, Any]) -> DataProcessorOutput:
    """Filter data based on criteria"""
    try:
        filter_key = parameters.get("key")
        filter_value = parameters.get("value")
        filter_operator = parameters.get("operator", "eq")  # eq, gt, lt, contains
        
        if not filter_key or filter_value is None:
            return DataProcessorOutput(
                success=False,
                processed_data={},
                statistics={"error": "Missing filter key or value"}
            )
        
        if isinstance(data, dict):
            # Filter dictionary
            if filter_operator == "eq":
                filtered = {k: v for k, v in data.items() if v == filter_value}
            elif filter_operator == "contains":
                filtered = {k: v for k, v in data.items() if str(filter_value) in str(v)}
            else:
                filtered = data
        elif isinstance(data, list):
            # Filter list of dictionaries
            if filter_operator == "eq":
                filtered = [item for item in data if item.get(filter_key) == filter_value]
            elif filter_operator == "contains":
                filtered = [item for item in data if str(filter_value) in str(item.get(filter_key, ""))]
            else:
                filtered = data
        else:
            filtered = data
        
        return DataProcessorOutput(
            success=True,
            processed_data={"filtered": filtered},
            statistics={
                "original_count": len(data) if isinstance(data, (list, dict)) else 1,
                "filtered_count": len(filtered) if isinstance(filtered, (list, dict)) else 1,
                "filter_criteria": f"{filter_key} {filter_operator} {filter_value}"
            }
        )
    except Exception as e:
        return DataProcessorOutput(
            success=False,
            processed_data={},
            statistics={"error": f"Filter operation failed: {str(e)}"}
        )

def _sort_data(data: Dict[str, Any], parameters: Dict[str, Any]) -> DataProcessorOutput:
    """Sort data based on criteria"""
    try:
        sort_key = parameters.get("key")
        reverse = parameters.get("reverse", False)
        
        if not sort_key:
            return DataProcessorOutput(
                success=False,
                processed_data={},
                statistics={"error": "Missing sort key"}
            )
        
        if isinstance(data, list):
            # Sort list of dictionaries
            sorted_data = sorted(data, key=lambda x: x.get(sort_key, 0), reverse=reverse)
        elif isinstance(data, dict):
            # Sort dictionary by values
            sorted_data = dict(sorted(data.items(), key=lambda x: x[1], reverse=reverse))
        else:
            sorted_data = data
        
        return DataProcessorOutput(
            success=True,
            processed_data={"sorted": sorted_data},
            statistics={
                "sort_key": sort_key,
                "reverse": reverse,
                "count": len(sorted_data) if isinstance(sorted_data, (list, dict)) else 1
            }
        )
    except Exception as e:
        return DataProcessorOutput(
            success=False,
            processed_data={},
            statistics={"error": f"Sort operation failed: {str(e)}"}
        )

def _aggregate_data(data: Dict[str, Any], parameters: Dict[str, Any]) -> DataProcessorOutput:
    """Aggregate data based on criteria"""
    try:
        agg_key = parameters.get("key")
        agg_operation = parameters.get("operation", "sum")  # sum, avg, count, min, max
        
        if not agg_key:
            return DataProcessorOutput(
                success=False,
                processed_data={},
                statistics={"error": "Missing aggregation key"}
            )
        
        if isinstance(data, list):
            values = [item.get(agg_key, 0) for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            values = list(data.values())
        else:
            values = [data]
        
        # Perform aggregation
        if agg_operation == "sum":
            result = sum(values)
        elif agg_operation == "avg":
            result = sum(values) / len(values) if values else 0
        elif agg_operation == "count":
            result = len(values)
        elif agg_operation == "min":
            result = min(values) if values else 0
        elif agg_operation == "max":
            result = max(values) if values else 0
        else:
            result = 0
        
        return DataProcessorOutput(
            success=True,
            processed_data={"aggregated": result},
            statistics={
                "aggregation_key": agg_key,
                "operation": agg_operation,
                "input_count": len(values),
                "result": result
            }
        )
    except Exception as e:
        return DataProcessorOutput(
            success=False,
            processed_data={},
            statistics={"error": f"Aggregation operation failed: {str(e)}"}
        )

def _transform_data(data: Dict[str, Any], parameters: Dict[str, Any]) -> DataProcessorOutput:
    """Transform data based on rules"""
    try:
        transform_type = parameters.get("type", "rename")  # rename, scale, format
        rules = parameters.get("rules", {})
        
        if transform_type == "rename":
            # Rename keys
            if isinstance(data, dict):
                transformed = {}
                for old_key, new_key in rules.items():
                    if old_key in data:
                        transformed[new_key] = data[old_key]
                    else:
                        transformed[old_key] = data.get(old_key)
                # Keep keys not in rules
                for key, value in data.items():
                    if key not in rules:
                        transformed[key] = value
            else:
                transformed = data
        elif transform_type == "scale":
            # Scale numeric values
            scale_factor = parameters.get("scale_factor", 1.0)
            if isinstance(data, dict):
                transformed = {k: v * scale_factor if isinstance(v, (int, float)) else v for k, v in data.items()}
            elif isinstance(data, list):
                transformed = [item * scale_factor if isinstance(item, (int, float)) else item for item in data]
            else:
                transformed = data * scale_factor if isinstance(data, (int, float)) else data
        elif transform_type == "format":
            # Format values
            format_template = parameters.get("format_template", "{value}")
            if isinstance(data, dict):
                transformed = {k: format_template.format(value=v, key=k) for k, v in data.items()}
            else:
                transformed = format_template.format(value=data)
        else:
            transformed = data
        
        return DataProcessorOutput(
            success=True,
            processed_data={"transformed": transformed},
            statistics={
                "transform_type": transform_type,
                "rules_applied": len(rules),
                "input_type": type(data).__name__,
                "output_type": type(transformed).__name__
            }
        )
    except Exception as e:
        return DataProcessorOutput(
            success=False,
            processed_data={},
            statistics={"error": f"Transform operation failed: {str(e)}"}
        ) 