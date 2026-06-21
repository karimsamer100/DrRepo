"""Report renderers for DrRepo.

This package exposes report generation utilities.
"""

from .markdown_report import render_markdown_report
from .terminal_summary import render_terminal_summary

__all__ = ["render_markdown_report", "render_terminal_summary"]
