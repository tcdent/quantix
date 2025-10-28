"""
Quantix - Pure Python interface for Quantis Quantum Random Number Generators

This module provides direct access to Quantis PCI devices through /dev/qrandom*
character device files. Reverse-engineered from scratch - no C library required.

Developed for Quantis PCI 16Mbps cards (circa 2013) on Linux kernel 6.1+.

The original ID Quantique software (2013) provided only a C library with no Python
implementation. Rather than port the aging C codebase, we reverse-engineered the
interface and implemented it directly in pure Python.

License: MIT
"""

import fcntl
import glob
import struct
from enum import IntEnum
from pathlib import Path
from typing import BinaryIO, cast

__all__ = [
    "DeviceType",
    "Quantix",
    "QuantixException",
    "count_devices",
]


# Device path configuration
DEV_PREFIX = "/dev/qrandom"

# ioctl constants from quantis_pci.h
# These allow us to query device information and control the hardware
_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2


def _IOC(dir: int, type: str, nr: int, size: int) -> int:
    """Construct an ioctl command number"""
    return (
        (dir << _IOC_DIRSHIFT)
        | (ord(type) << _IOC_TYPESHIFT)
        | (nr << _IOC_NRSHIFT)
        | (size << _IOC_SIZESHIFT)
    )


def _IOR(type: str, nr: int, size: int) -> int:
    """Construct a read ioctl command"""
    return _IOC(_IOC_READ, type, nr, size)


def _IOW(type: str, nr: int, size: int) -> int:
    """Construct a write ioctl command"""
    return _IOC(_IOC_WRITE, type, nr, size)


def _IO(type: str, nr: int) -> int:
    """Construct a simple ioctl command (no data transfer)"""
    return _IOC(_IOC_NONE, type, nr, 0)


# Quantis ioctl commands (magic number 'q')
QUANTIS_IOCTL_GET_DRIVER_VERSION = _IOR("q", 0, 4)  # unsigned int = 4 bytes
QUANTIS_IOCTL_GET_CARD_COUNT = _IOR("q", 1, 4)
QUANTIS_IOCTL_GET_MODULES_MASK = _IOR("q", 2, 4)
QUANTIS_IOCTL_GET_BOARD_VERSION = _IOR("q", 3, 4)
QUANTIS_IOCTL_RESET_BOARD = _IO("q", 4)
QUANTIS_IOCTL_ENABLE_MODULE = _IOW("q", 5, 4)
QUANTIS_IOCTL_DISABLE_MODULE = _IOW("q", 6, 4)
QUANTIS_IOCTL_GET_MODULES_STATUS = _IOR("q", 8, 4)
QUANTIS_IOCTL_GET_PCI_BUS_DEVICE_ID = _IOR("q", 9, 4)

IOCTL_READ_OPS = {
    QUANTIS_IOCTL_GET_DRIVER_VERSION,
    QUANTIS_IOCTL_GET_CARD_COUNT,
    QUANTIS_IOCTL_GET_MODULES_MASK,
    QUANTIS_IOCTL_GET_BOARD_VERSION,
    QUANTIS_IOCTL_GET_MODULES_STATUS,
    QUANTIS_IOCTL_GET_PCI_BUS_DEVICE_ID,
}
IOCTL_WRITE_OPS = {
    QUANTIS_IOCTL_ENABLE_MODULE,
    QUANTIS_IOCTL_DISABLE_MODULE,
}


class DeviceType(IntEnum):
    """Type of Quantis device"""

    PCI = 1
    USB = 2  # Not supported in this implementation


class QuantixException(Exception):
    """Exception raised for Quantis device errors"""

    def __init__(self, message: str, device_path: str | None = None):
        self.device_path = device_path
        super().__init__(message)


def count_devices(device_type: DeviceType = DeviceType.PCI) -> int:
    """
    Count the number of Quantis devices

    Args:
        device_type: Type of device to count (only PCI supported)

    Returns:
        Number of devices detected (0 if none)
    """
    if device_type == DeviceType.USB:
        return 0  # USB not supported in this implementation

    # Count device nodes matching DEV_PREFIX
    devices = glob.glob(f"{DEV_PREFIX}*")
    return len(devices)


class Quantix:
    """
    Interface to a Quantis Quantum Random Number Generator

    This class provides direct access to the quantum RNG hardware through
    the /dev/qrandom* device files created by the kernel driver.
    """

    # Class variable type annotations
    device_type: DeviceType
    device_number: int
    device_path: str
    _fd: BinaryIO | None  # file object or None

    def __init__(self, device_type: DeviceType = DeviceType.PCI, device_number: int = 0):
        """
        Initialize a Quantis device instance

        Args:
            device_type: Type of device (only PCI supported)
            device_number: Device index (0-based)

        Raises:
            QuantixException: If device not found

        Note:
            Use as a context manager to automatically handle device open/close:
                qrng = Quantix(DeviceType.PCI, 0)
                with qrng:
                    data = qrng.read(16)
        """
        # Initialize _fd first so __del__ won't fail if __init__ raises
        self._fd = None

        if device_type == DeviceType.USB:
            raise QuantixException("USB devices not supported")

        self.device_type = device_type
        self.device_number = device_number
        self.device_path = f"{DEV_PREFIX}{device_number}"

        # Verify device exists
        if not Path(self.device_path).exists():
            raise QuantixException(
                f"Device {self.device_path} not found. Is the driver loaded?",
                self.device_path,
            )

    def __repr__(self) -> str:
        return f"Quantix(device_type={self.device_type.name}, device_number={self.device_number})"

    def __enter__(self) -> "Quantix":
        """Context manager entry - opens the device"""
        if self._fd is None:
            try:
                self._fd = open(self.device_path, "rb", buffering=0)
            except PermissionError:
                raise QuantixException(f"Permission denied for {self.device_path}. ", self.device_path)
            except Exception as e:
                raise QuantixException(f"Cannot access {self.device_path}: {e}", self.device_path)
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit - closes the device"""
        self.close()

    def __del__(self) -> None:
        """Destructor - ensure file descriptor is closed"""
        self.close()

    def close(self) -> None:
        """Close the device file descriptor"""
        if self._fd is not None:
            try:
                self._fd.close()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._fd = None

    def _ioctl(self, request: int, arg: int = 0) -> int:
        """
        Perform an ioctl operation on the device

        Args:
            request: ioctl request code
            arg: argument value for write operations

        Returns:
            Result value from the ioctl call

        Raises:
            QuantixException: If ioctl fails or device is closed
        """
        if self._fd is None:
            raise QuantixException(
                "Device is not open. Use 'with Quantix(...) as qrng:' to open the device.",
                self.device_path,
            )

        try:
            # For read operations, we need a buffer to receive the value
            if request in IOCTL_READ_OPS:
                buf = struct.pack("I", 0)
                result = fcntl.ioctl(self._fd.fileno(), request, buf)
                return cast(int, struct.unpack("I", result)[0])
            # For write operations
            elif request in IOCTL_WRITE_OPS:
                buf = struct.pack("I", arg)
                fcntl.ioctl(self._fd.fileno(), request, buf)
                return 0
            # For simple operations (no data)
            else:
                fcntl.ioctl(self._fd.fileno(), request)
                return 0
        except OSError as e:
            raise QuantixException(f"ioctl failed on {self.device_path}: {e}", self.device_path)

    # Device information methods

    def get_driver_version(self) -> float:
        """
        Get the driver version

        Returns:
            Driver version as float (e.g., 2.1)

        Raises:
            QuantixException: If operation fails
        """
        version = self._ioctl(QUANTIS_IOCTL_GET_DRIVER_VERSION)
        return version / 10.0

    def get_board_version(self) -> int:
        """
        Get the board hardware version

        Returns:
            Board version as integer

        Raises:
            QuantixException: If operation fails
        """
        return self._ioctl(QUANTIS_IOCTL_GET_BOARD_VERSION)

    def get_modules_mask(self) -> int:
        """
        Get bitmask of available quantum modules

        Each bit represents one quantum module (0-3).
        A set bit indicates the module is present.

        Returns:
            Bitmask of available modules (0-15)

        Raises:
            QuantixException: If operation fails
        """
        return self._ioctl(QUANTIS_IOCTL_GET_MODULES_MASK)

    def get_modules_status(self) -> int:
        """
        Get bitmask of working quantum modules

        Each bit represents one quantum module (0-3).
        A set bit indicates the module is functioning.

        Returns:
            Bitmask of working modules (0-15)

        Raises:
            QuantixException: If operation fails
        """
        return self._ioctl(QUANTIS_IOCTL_GET_MODULES_STATUS)

    def get_modules_count(self) -> int:
        """
        Get the number of working quantum modules

        Returns:
            Number of working modules (0-4)

        Raises:
            QuantixException: If operation fails
        """
        status = self.get_modules_status()
        return bin(status).count("1")

    def reset_board(self) -> None:
        """
        Reset the Quantis board

        Raises:
            QuantixException: If operation fails
        """
        self._ioctl(QUANTIS_IOCTL_RESET_BOARD)

    def enable_module(self, module: int) -> None:
        """
        Enable a specific quantum module

        Args:
            module: Module number (0-3)

        Raises:
            QuantixException: If operation fails
            ValueError: If module number is invalid
        """
        if not 0 <= module <= 3:
            raise ValueError("Module number must be 0-3")
        self._ioctl(QUANTIS_IOCTL_ENABLE_MODULE, module)

    def disable_module(self, module: int) -> None:
        """
        Disable a specific quantum module

        Args:
            module: Module number (0-3)

        Raises:
            QuantixException: If operation fails
            ValueError: If module number is invalid
        """
        if not 0 <= module <= 3:
            raise ValueError("Module number must be 0-3")
        self._ioctl(QUANTIS_IOCTL_DISABLE_MODULE, module)

    def get_pci_info(self) -> tuple[int, int]:
        """
        Get PCI bus and device ID

        Returns:
            Tuple of (bus_id, device_id)

        Raises:
            QuantixException: If operation fails
        """
        value = self._ioctl(QUANTIS_IOCTL_GET_PCI_BUS_DEVICE_ID)
        bus_id = (value >> 16) & 0xFFFF
        device_id = value & 0xFFFF
        return (bus_id, device_id)

    # Random data reading methods

    def read(self, size: int) -> bytes:
        """
        Read random bytes from the quantum RNG

        Args:
            size: Number of bytes to read

        Returns:
            Random bytes

        Raises:
            QuantixException: If read fails or device is closed
            ValueError: If size is negative or zero
        """
        if size <= 0:
            raise ValueError("Size must be positive")

        if self._fd is None:
            raise QuantixException(
                "Device is not open. Use 'with Quantix(...) as qrng:' to open the device.",
                self.device_path,
            )

        try:
            data = self._fd.read(size)

            if len(data) != size:
                raise QuantixException(f"Read {len(data)} bytes, expected {size}", self.device_path)

            return data

        except QuantixException:
            raise
        except Exception as e:
            raise QuantixException(f"Failed to read from {self.device_path}: {e}", self.device_path)

    def read_int(self) -> int:
        """
        Read a random 32-bit unsigned integer

        Returns:
            Random integer (0 to 2^32-1)

        Raises:
            QuantixException: If read fails
        """
        data = self.read(4)
        return cast(int, struct.unpack("I", data)[0])

    def read_short(self) -> int:
        """
        Read a random 16-bit unsigned integer

        Returns:
            Random integer (0 to 2^16-1)

        Raises:
            QuantixException: If read fails
        """
        data = self.read(2)
        return cast(int, struct.unpack("H", data)[0])

    def read_float(self) -> float:
        """
        Read a random float in range [0.0, 1.0)

        Returns:
            Random float

        Raises:
            QuantixException: If read fails
        """
        # Use 32 bits of entropy to generate float in [0, 1)
        value = self.read_int()
        return value / (2**32)

    def read_double(self) -> float:
        """
        Read a random double in range [0.0, 1.0)

        Returns:
            Random double

        Raises:
            QuantixException: If read fails
        """
        # Use 64 bits of entropy for better precision
        data = self.read(8)
        value = cast(int, struct.unpack("Q", data)[0])
        return value / (2**64)

    def read_int_range(self, min_val: int, max_val: int) -> int:
        """
        Read a random integer in a specific range

        Args:
            min_val: Minimum value (inclusive)
            max_val: Maximum value (inclusive)

        Returns:
            Random integer in range [min_val, max_val]

        Raises:
            QuantixException: If read fails
            ValueError: If min_val > max_val
        """
        if min_val > max_val:
            raise ValueError("min_val must be <= max_val")

        range_size = max_val - min_val + 1
        value = self.read_int()
        return min_val + (value % range_size)

    def read_bytes_list(self, size: int) -> list[int]:
        """
        Read random bytes as a list of integers

        Args:
            size: Number of bytes to read

        Returns:
            List of random bytes as integers (0-255)

        Raises:
            QuantixException: If read fails
        """
        data = self.read(size)
        return list(data)
