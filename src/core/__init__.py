"""Core infrastructure for TrainSign."""
from .matrix import import_matrix, load_matrix

# Note: SampleBase is not imported here to avoid circular imports with transit
# Import it directly with: from core.base import SampleBase

__all__ = ["import_matrix", "load_matrix"]
