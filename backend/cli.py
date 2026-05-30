#!/usr/bin/env python3
"""Amphoreus Story Engine — Interactive CLI.

Entry point shim. The implementation lives in the ``app.cli`` package:

  1. Language selection (中文 / English)
  2. API key check (with prompt to configure if missing)
  3. Mode selection: new world / upload document / continue project
  4. World building (conversational LLM-guided)
  5. Character generation (with inline editing)
  6. Relationship inference
  7. Plot architecture (structure selection + outline)
  8. Scene execution (round-by-round display)
  9. Narrative writing (novel/screenplay conversion + file export)
"""

from __future__ import annotations

from app.cli.main import main

if __name__ == "__main__":
    main()
