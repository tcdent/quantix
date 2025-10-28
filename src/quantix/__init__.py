"""
Quantix - Pure Python interface for Quantis Quantum Random Number Generators

This package provides direct access to ID Quantique Quantis quantum random
number generators (PCI/PCIe models) through /dev/qrandom* device files.

This is an independent, clean-room implementation not affiliated with ID Quantique.

Example:
    >>> from quantix import Quantix, DeviceType
    >>>
    >>> # Initialize device and use as context manager
    >>> qrng = Quantix(DeviceType.PCI, device_number=0)
    >>> with qrng:
    >>>     # Read random bytes
    >>>     random_bytes = qrng.read(16)
    >>>
    >>>     # Read random integer
    >>>     random_int = qrng.read_int()
    >>>
    >>>     # Read random float in range [0.0, 1.0)
    >>>     random_float = qrng.read_float()
"""

from importlib.metadata import version, PackageNotFoundError

from .quantix import (
    Quantix,
    DeviceType,
    QuantixException,
    count_devices,
)

try:
    __version__ = version("quantix")
except PackageNotFoundError:
    # Package not installed, use fallback
    __version__ = "0.0.0+dev"

__all__ = [
    "Quantix",
    "DeviceType",
    "QuantixException",
    "count_devices",
]
