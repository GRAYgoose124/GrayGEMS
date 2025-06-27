"""
Text Processing Tasks for GrayGEMS Demo
Demonstrates how to create text analysis services using GrayGEMS
"""

import asyncio
from typing import Dict, Any
from pathlib import Path
from graygems.core.service import Task


class WordCountTask(Task):
    """Count words in text"""

    async def execute(
        self, inputs: Dict[str, Any], project_dir: Path
    ) -> Dict[str, Any]:
        text = inputs.get("text", "")

        # Simple word counting (split by whitespace)
        words = text.split()
        word_count = len(words)

        # Count unique words
        unique_words = len(set(words))

        return {
            "outputs": {
                "word_count": word_count,
                "unique_words": unique_words,
                "text_length": len(text),
                "inputs": {"text": text},
            }
        }


class CharacterCountTask(Task):
    """Count characters in text"""

    async def execute(
        self, inputs: Dict[str, Any], project_dir: Path
    ) -> Dict[str, Any]:
        text = inputs.get("text", "")

        # Count different types of characters
        total_chars = len(text)
        letters = sum(1 for c in text if c.isalpha())
        digits = sum(1 for c in text if c.isdigit())
        spaces = sum(1 for c in text if c.isspace())
        punctuation = sum(1 for c in text if c in ".,!?;:")

        return {
            "outputs": {
                "total_characters": total_chars,
                "letters": letters,
                "digits": digits,
                "spaces": spaces,
                "punctuation": punctuation,
                "inputs": {"text": text},
            }
        }


# Wrapper functions for the service registration
async def word_count(inputs: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
    """Count words in text - wrapper function"""
    task = WordCountTask()
    return await task.execute(inputs, project_dir)


async def character_count(inputs: Dict[str, Any], project_dir: Path) -> Dict[str, Any]:
    """Count characters in text - wrapper function"""
    task = CharacterCountTask()
    return await task.execute(inputs, project_dir)
