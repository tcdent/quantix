# Quantix

Pure Python interface for ID Quantique Quantis Quantum Random Number Generators.

This is an independent, clean-room implementation that provides direct access to Quantis PCI/PCIe quantum RNG devices through `/dev/qrandom*` device files.

## Background

This library was created to modernize access to quantum random number generators on Linux. The original ID Quantique software from 2013 included only a C library (`libQuantis`) with no Python implementation.

Rather than try to bring forward compatibility to the aging C library codebase, we **reverse-engineered the interface and wrote a pure Python implementation from scratch**. The result is a modern, type-safe library with zero C dependencies.

**Hardware**: Developed for and tested with a **Quantis PCI 16Mbps** card (circa 2013) on kernel 6.1.

This project includes:
- A **pure Python library** (this package) - reverse-engineered from scratch
- A **ported kernel driver** ([quantis-pci](https://github.com/tcdent/QuantisPci)) - updated from 2013 source for kernel 6.1+ compatibility

The kernel driver required significant updates:
- **Porting work**: Modernized APIs (access_ok, ioremap, proc_fs), fixed deprecated functions
- **Critical bug fixes**:
  - Removed obsolete Big Kernel Lock (BKL) that caused "scheduling while atomic" kernel oops
  - Fixed PCI BAR reservation to only request BAR 1 (the driver was incorrectly trying to reserve all BARs, causing -EBUSY errors)

Without these fixes, the driver would not load or would crash when performing ioctl operations on kernel 6.1+.

## Features

- ✅ **Pure Python** (3.9+) with full type hints
- ✅ **Zero dependencies** - uses only standard library
- ✅ **Direct device access** - reads from `/dev/qrandom*`
- ✅ **Context manager support** - automatic resource management
- ✅ **Complete ioctl API** - device info, module control, etc.
- ✅ **Type-safe** - full mypy compliance with `py.typed`
- ✅ **Efficient** - unbuffered reads for maximum throughput
- ✅ **Clean API** - Pythonic interface

## Installation

### Prerequisites

1. **Quantis kernel driver** must be loaded:
   ```bash
   sudo modprobe quantis_pci
   ```

2. **Device permissions**: Add your user to the `quantis` group:
   ```bash
   sudo usermod -a -G quantis $USER
   # Log out and back in for group changes to take effect
   ```

### Install Quantix

```bash
# From PyPI
pip install quantix

# Or with uv (recommended)
uv pip install quantix
```

### Development Installation

```bash
# Clone the repository
git clone https://github.com/tcdent/quantix.git
cd quantix

# Install in editable mode with dev dependencies
uv sync
# or
pip install -e ".[dev]"
```

## Quick Start

```python
from quantix import Quantix, DeviceType

# Initialize device
qrng = Quantix(DeviceType.PCI, device_number=0)

# Use as context manager (recommended)
with qrng:
    # Read 16 random bytes
    random_bytes = qrng.read(16)
    print(f"Random bytes: {random_bytes.hex()}")

    # Read random integer
    random_int = qrng.read_int()
    print(f"Random int: {random_int}")

    # Read random float [0.0, 1.0)
    random_float = qrng.read_float()
    print(f"Random float: {random_float}")
```

## API Examples

### Device Information

```python
with Quantix(DeviceType.PCI, 0) as qrng:
    # Get device information via ioctl
    driver_version = qrng.get_driver_version()
    board_version = qrng.get_board_version()
    modules_count = qrng.get_modules_count()

    print(f"Driver: v{driver_version}")
    print(f"Board: 0x{board_version:08x}")
    print(f"Working modules: {modules_count}")
```

### Reading Random Data

```python
with Quantix(DeviceType.PCI, 0) as qrng:
    # Read bytes
    data = qrng.read(1024)

    # Read typed values
    value_int = qrng.read_int()          # 32-bit unsigned
    value_short = qrng.read_short()      # 16-bit unsigned
    value_float = qrng.read_float()      # [0.0, 1.0)
    value_double = qrng.read_double()    # [0.0, 1.0) higher precision

    # Read in range
    dice_roll = qrng.read_int_range(1, 6)  # 1-6 inclusive
```

### Module Control

```python
with Quantix(DeviceType.PCI, 0) as qrng:
    # Get module status
    mask = qrng.get_modules_mask()      # Available modules
    status = qrng.get_modules_status()  # Working modules

    # Control modules
    qrng.enable_module(0)
    qrng.disable_module(1)

    # Reset board
    qrng.reset_board()
```

## Architecture

Quantix uses pure Python to interact directly with the Quantis hardware:

```
┌──────────────┐
│   Python     │
│  Application │
└──────┬───────┘
       │ Quantix (Pure Python)
       │ - open(/dev/qrandom0)
       │ - read() syscall
       │ - ioctl() for device info
       ▼
┌──────────────┐
│    Kernel    │
│    Driver    │  quantis_pci.ko
└──────┬───────┘
       │ Memory-mapped I/O
       ▼
┌──────────────┐
│   Quantis    │
│   Hardware   │  PCI device
└──────────────┘
```

No C library required! Direct syscalls for maximum simplicity.

## Why Quantix?

The original `libQuantis` C library from 2013 has compatibility issues with modern systems (segfaults, deprecated threading, C++17 incompatibility). Quantix provides a clean, modern alternative:

- **No compilation needed** - pure Python
- **No CFFI/ctypes complexity** - direct syscalls
- **Modern Python practices** - type hints, context managers
- **Better error messages** - Pythonic exceptions
- **Maintainable** - easy to read and modify

## Testing

```bash
# Run all tests
make test

# Run with verbose output
make test-verbose
```

All tests require actual hardware and proper permissions.

## Development

```bash
# Install development dependencies
uv sync

# Run tests
pytest tests/ -v

# Check types
mypy src/

# Format code
black src/ tests/
```

## License

MIT License - see LICENSE file for details.

This is an independent implementation not affiliated with ID Quantique.

## Hardware Support

Currently supported:
- ✅ Quantis PCI 16Mbps
- ✅ Quantis PCIe (via PCI driver)

Not yet supported:
- ❌ Quantis USB (contributions welcome!)

## Troubleshooting

### Permission Denied

```bash
# Add user to quantis group
sudo usermod -a -G quantis $USER

# Verify group membership
groups | grep quantis

# If not showing, log out and back in or run:
newgrp quantis
```

### No Device Found

```bash
# Check if driver is loaded
lsmod | grep quantis

# Check if device exists
ls -l /dev/qrandom*

# Load driver if needed
sudo modprobe quantis_pci
```

### Multiple Devices

```python
# List all devices
from quantix import count_devices, DeviceType

count = count_devices(DeviceType.PCI)
print(f"Found {count} PCI devices")

# Access specific device
with Quantix(DeviceType.PCI, device_number=1) as qrng:
    data = qrng.read(16)
```

## Contributing

Contributions welcome! Please ensure:
- Tests pass (`make test`)
- Type checks pass (`uv run mypy src/quantix/`)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## References

- [ID Quantique Quantis](https://www.idquantique.com/random-number-generation/products/quantis-rng/)
- [Quantis PCI Driver (community fork)](https://github.com/tcdent/QuantisPci)
