"""flagconv: convert feature flag definitions between formats."""

from .converter import ConversionError, flat_to_ld, ld_to_flat

__all__ = ["ConversionError", "flat_to_ld", "ld_to_flat"]
__version__ = "0.1.0"
