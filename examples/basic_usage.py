#!/usr/bin/env python3
"""
Basic usage example for PyQuantix

Demonstrates simple random number generation from Quantis quantum RNG.
"""

from quantix import Quantix, DeviceType, count_devices


def main():
    print("=" * 60)
    print("PyQuantix - Basic Usage Example")
    print("=" * 60)
    print()

    # Count devices
    pci_count = count_devices(DeviceType.PCI)
    usb_count = count_devices(DeviceType.USB)
    print(f"PCI devices: {pci_count}")
    print(f"USB devices: {usb_count}")
    print()

    if pci_count == 0 and usb_count == 0:
        print("No Quantis devices found!")
        return

    # Initialize device (use first PCI device)
    print("Initializing Quantis device...")
    qrng = Quantix(DeviceType.PCI, device_number=0)
    print(f"Device: {qrng}")
    print(f"Device path: {qrng.device_path}")
    print()

    # Read random bytes
    print("Reading 16 random bytes:")
    random_bytes = qrng.read(16)
    print(f"  Hex: {random_bytes.hex()}")
    print(f"  List: {list(random_bytes)}")
    print()

    # Read random integers
    print("Reading 5 random integers (0-100):")
    for i in range(5):
        value = qrng.read_int_range(0, 100)
        print(f"  {value}")
    print()

    # Read random floats
    print("Reading 5 random floats (0.0-1.0):")
    for i in range(5):
        value = qrng.read_float()
        print(f"  {value:.10f}")
    print()

    # Read random doubles
    print("Reading 5 random doubles (0.0-1.0):")
    for i in range(5):
        value = qrng.read_double()
        print(f"  {value:.15f}")
    print()

    # Read large random numbers
    print(f"Random 16-bit integer: {qrng.read_short()}")
    print(f"Random 32-bit integer: {qrng.read_int()}")
    print()

    print("Done!")


if __name__ == "__main__":
    main()
