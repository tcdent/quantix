# Quantix

Pure Python interface for ID Quantique Quantis Quantum Random Number Generators.

This is an independent, clean-room implementation that provides direct access to Quantis PCI/PCIe and USB quantum RNG devices through `/dev/qrandom*` and `pyusb` device files.

## Background

This library was created to modernize access to quantum random number generators on Linux. The original ID Quantique software from 2013 included only a C library (`libQuantis`) with no Python implementation.

Rather than try to bring forward compatibility to the aging C library codebase, we **reverse-engineered the interface and wrote a pure Python implementation from scratch**. The result is a modern, type-safe library with zero C dependencies.

**Hardware**: Developed for and tested with a **Quantis PCI 16Mbps** card (circa 2013) on kernel 6.1 and **Quantis USB** module.

This project includes:
- A **pure Python library** (this package) - reverse-engineered from scratch
- A **ported kernel driver** ([quantis-pci](https://github.com/tcdent/QuantisPci)) - updated from 2013 source for kernel 6.1+ compatibility

The kernel driver required significant updates:
- **Porting work**: Modernized APIs (access_ok, ioremap, proc_fs), fixed deprecated functions
- **Critical bug fixes**:
  - Removed obsolete Big Kernel Lock (BKL) that caused "scheduling while atomic" kernel oops
  - Fixed PCI BAR reservation to only request BAR 1 (the driver was incorrectly trying to reserve all BARs, causing -EBUSY errors)

Without these fixes, the driver would not load or would crash when performing ioctl operations on kernel 6.1+.

## Installation

### Prerequisites

- PCI

1. **Quantis kernel driver** must be loaded:
   ```bash
   sudo modprobe quantis_pci
   ```

2. **Device permissions**: Add your user to the `quantis` group:
   ```bash
   sudo usermod -a -G quantis $USER
   # Log out and back in for group changes to take effect
   ```

- USB

1. **Device permissions**: No kernel module needed. User access by group "pludev" per udev rules.

   /etc/udev/rules.d/70-quantis-usb.rules:
   ```txt
   SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", ATTR{idVendor}=="0aba", ATTR{idProduct}=="0102", MODE="0660", GROUP="plugdev", TAG+="uaccess" 
   ```

   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

   ```bash
   ls -l /dev/bus/usb/*
   /dev/bus/usb/001:
   [..]
   crw-rw---- 1 root plugdev 189, 4 Nov 12 09:22 005
   crw-rw---- 1 root plugdev 189, 5 Nov 12 09:22 006
   [..]
   ```

2. **User permissions**: Add your user to the `plugdev` group:
   ```bash
   sudo usermod -a -G plugdev $USER
   # Log out and back in for group changes to take effect
   ```

### Install Quantix

```bash
# From PyPI
pip install quantix-rng

# Or with uv (recommended)
uv pip install quantix-rng
```

**Note**: The package name is `quantix-rng` but you import it as `quantix`:
```python
from quantix import Quantix, DeviceType
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

- PCI

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

- USB

```python
from quantix import Quantix, DeviceType

# Initialize device
qrng = Quantix(DeviceType.USB, device_number=0)

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

- PCI

```python
from quantix import Quantix, DeviceType

with Quantix(DeviceType.PCI, 0) as qrng:
    # Get device information via ioctl
    driver_version = qrng.get_driver_version()
    board_version = qrng.get_board_version()
    modules_count = qrng.get_modules_count()

    print(f"Driver: v{driver_version}")
    print(f"Board: 0x{board_version:08x}")
    print(f"Working modules: {modules_count}")
``` 

- USB

```python
from quantix import Quantix, DeviceType

with Quantix(DeviceType.USB, 0) as qrng:
    # Get device information via libusb
    driver_version = qrng.get_driver_version()
    board_version = qrng.get_board_version()
    modules_count = qrng.get_modules_count()

    print(f"Driver: v{driver_version}")
    print(f"Board: 0x{board_version:08x}")
    print(f"Working modules: {modules_count}")
```

### Reading Random Data

- PCI

```python
from quantix import Quantix, DeviceType

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

- USB

```python
from quantix import Quantix, DeviceType

with Quantix(DeviceType.USB, 0) as qrng:
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

- PCI

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

- USB

```python
from quantix import Quantix, DeviceType

with Quantix(DeviceType.USB, 0) as qrng:
    # Get module status
    mask = qrng.get_modules_mask()      # Available modules
    status = qrng.get_modules_status()  # Working modules

    # Control modules
    qrng.enable_module(0)
    qrng.disable_module(0)

    # Reset board
    qrng.reset_board()
```

## Architecture

Quantix uses pure Python to interact directly with the Quantis hardware:

- PCI

No C library required! Direct syscalls for maximum simplicity.

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

- USB

Only userspace "pyusb" (libusb1.0) needed.

```
┌──────────────┐
│   Python     │
│  Application │
└──────┬───────┘
       │ Quantix (Pure Python)
       │ - pyusb via syscalls
       ▼
┌──────────────┐
│    Kernel    │
└──────┬───────┘
       │ 
       ▼
┌──────────────┐
│   Quantis    │
│   Hardware   │  USB device
└──────────────┘
```



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
- ✅ Quantis USB (via pyusb)

## Troubleshooting

### Permission Denied (PCI)

```bash
# Add user to quantis group
sudo usermod -a -G quantis $USER

# Verify group membership
groups | grep quantis

# If not showing, log out and back in or run:
newgrp quantis
```

### Permission Denied (USB)

```bash
# Add user to quantis group
sudo usermod -a -G plugdev $USER

# Verify group membership
id -a $USER
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

- PCI

```python
# List all devices
from quantix import count_devices, DeviceType

count = count_devices(DeviceType.PCI)
print(f"Found {count} PCI devices")

# Access specific device
with Quantix(DeviceType.PCI, device_number=1) as qrng:
    data = qrng.read(16)
```

- USB

```python
from quantix import Quantix, DeviceType, count_devices

for i in range(count_devices(DeviceType.USB)):
    with Quantix(DeviceType.USB, i) as q:
        print(f"usb device: {i}\n"
              f"vendor: {q.get_manufacturer()}\n"
              f"product: {q.get_product()}\n"
              f"serial number: {q.get_serial_number()}\n"
              f"board 0x{q.get_board_version():08x}, status {q.get_modules_status()}\n")
```

## Contributing

Contributions welcome! Please ensure:
- Tests pass (`make test`)
- Type checks pass (`uv run mypy src/quantix/`)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## References

- [ID Quantique Quantis](https://www.idquantique.com/random-number-generation/products/quantis-rng/)
- [Quantis PCI Driver (community fork)](https://github.com/tcdent/quantis-pci)
- [Quantis Driver (PCI, USB)](https://github.com/sanddweller/QRNGPcieDriver/)
