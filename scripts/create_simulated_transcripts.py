#!/usr/bin/env python3
"""
Create simulated Claude Code transcripts to demonstrate behavior analysis.
These represent typical Claude Code usage patterns.
"""

import json
from pathlib import Path
import random

# Simulated transcript patterns
TRANSCRIPT_TEMPLATES = [
    # Pattern 1: Traditional grep + full file read + edit
    {
        "name": "traditional_workflow",
        "content": """
User: Fix the bug in the reranking module