"""
Calculator Tasks for GrayGEMS Demo
Demonstrates how to create simple services using GrayGEMS
"""

import asyncio
from typing import Dict, Any, List
from pathlib import Path
from graygems.core.service import Task


class AddTask(Task):
    """Add two numbers"""

    async def execute(
        self, inputs: Dict[str, Any], project_dir: Path
    ) -> Dict[str, Any]:
        a = inputs.get("a", 0)
        b = inputs.get("b", 0)
        result = a + b

        return {
            "outputs": {
                "result": result,
                "operation": "addition",
                "inputs": {"a": a, "b": b},
            }
        }


class MultiplyTask(Task):
    """Multiply two numbers"""

    async def execute(
        self, inputs: Dict[str, Any], project_dir: Path
    ) -> Dict[str, Any]:
        a = inputs.get("a", 0)
        b = inputs.get("b", 0)
        result = a * b

        return {
            "outputs": {
                "result": result,
                "operation": "multiplication",
                "inputs": {"a": a, "b": b},
            }
        }


class CalculateMeanTask(Task):
    """Calculate mean of a list of numbers"""

    async def execute(
        self, inputs: Dict[str, Any], project_dir: Path
    ) -> Dict[str, Any]:
        numbers = inputs.get("numbers", [])

        if not numbers:
            result = 0
        else:
            result = sum(numbers) / len(numbers)

        return {
            "outputs": {
                "result": result,
                "operation": "mean",
                "count": len(numbers),
                "inputs": {"numbers": numbers},
            }
        }


# Wrapper functions for the service registration
async def add(inputs: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
    """Add two numbers - wrapper function"""
    task = AddTask()
    return await task.execute(inputs, project_dir)


async def multiply(inputs: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
    """Multiply two numbers - wrapper function"""
    task = MultiplyTask()
    return await task.execute(inputs, project_dir)


async def calculate_mean(inputs: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
    """Calculate mean of a list of numbers - wrapper function"""
    task = CalculateMeanTask()
    return await task.execute(inputs, project_dir)
