#!/usr/bin/env python3
"""
Performance testing for Quantis quantum RNG

Measures throughput and compares different read methods.
"""

import time
from quantix import Quantix, DeviceType


def benchmark_read(qrng: Quantis, method_name: str, read_func, iterations: int = 1000):
    """Benchmark a read method"""
    print(f"Benchmarking {method_name}...")
    start = time.perf_counter()

    for _ in range(iterations):
        read_func()

    elapsed = time.perf_counter() - start
    ops_per_sec = iterations / elapsed

    print(f"  {iterations} iterations in {elapsed:.3f} seconds")
    print(f"  {ops_per_sec:.2f} operations/second")
    print()


def main():
    print("=" * 60)
    print("PyQuantix - Performance Test")
    print("=" * 60)
    print()

    # Initialize device
    qrng = Quantix(DeviceType.PCI, device_number=0)
    print(f"Device: {qrng}")
    print(f"Data rate: {qrng.get_modules_data_rate()} bytes/sec")
    print()

    # Test different block sizes for read()
    print("Testing read() with different block sizes:")
    for block_size in [16, 64, 256, 1024, 4096]:
        start = time.perf_counter()
        total_bytes = 0
        iterations = 1000

        for _ in range(iterations):
            data = qrng.read(block_size)
            total_bytes += len(data)

        elapsed = time.perf_counter() - start
        throughput = total_bytes / elapsed / 1024  # KB/s

        print(f"  Block size {block_size:5d} bytes: {throughput:8.2f} KB/s")

    print()

    # Test individual read methods
    benchmark_read(qrng, "read_int()", lambda: qrng.read_int(), iterations=1000)
    benchmark_read(qrng, "read_short()", lambda: qrng.read_short(), iterations=1000)
    benchmark_read(qrng, "read_float()", lambda: qrng.read_float(), iterations=1000)
    benchmark_read(qrng, "read_double()", lambda: qrng.read_double(), iterations=1000)
    benchmark_read(
        qrng, "read_int_range(0, 100)", lambda: qrng.read_int_range(0, 100), iterations=1000
    )
    benchmark_read(qrng, "read_scaled(0.0, 1.0)", lambda: qrng.read_scaled(0.0, 1.0), iterations=1000)

    print("Done!")


if __name__ == "__main__":
    main()
