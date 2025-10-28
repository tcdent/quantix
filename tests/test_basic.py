"""
Basic tests for pyquantis

These tests require actual hardware to run.
"""

import pytest
from quantix import Quantix, DeviceType, count_devices, QuantixException


def test_count_devices():
    """Test device counting"""
    pci_count = count_devices(DeviceType.PCI)
    assert isinstance(pci_count, int)
    assert pci_count >= 0


@pytest.fixture
def qrnx():
    """Fixture providing an opened Quantis device with proper cleanup"""
    count = count_devices(DeviceType.PCI)
    if count == 0:
        pytest.skip("No PCI devices available")

    device = Quantix(DeviceType.PCI, device_number=0)
    with device:
        yield device


def test_device_init(qrnx):
    """Test device initialization"""
    assert qrnx.device_type == DeviceType.PCI
    assert qrnx.device_number == 0
    assert qrnx.device_path == "/dev/qrandom0"


def test_device_repr(qrnx):
    """Test device string representation"""
    assert "PCI" in str(qrnx)
    assert "0" in str(qrnx)


def test_read_bytes(qrnx):
    """Test reading random bytes"""
    data = qrnx.read(16)
    assert isinstance(data, bytes)
    assert len(data) == 16


def test_read_large_bytes(qrnx):
    """Test reading larger amount of random bytes"""
    data = qrnx.read(1024)
    assert isinstance(data, bytes)
    assert len(data) == 1024


def test_read_int(qrnx):
    """Test reading random integer"""
    value = qrnx.read_int()
    assert isinstance(value, int)
    assert 0 <= value < 2**32


def test_read_short(qrnx):
    """Test reading random short"""
    value = qrnx.read_short()
    assert isinstance(value, int)
    assert 0 <= value < 2**16


def test_read_float(qrnx):
    """Test reading random float"""
    value = qrnx.read_float()
    assert isinstance(value, float)
    assert 0.0 <= value < 1.0


def test_read_double(qrnx):
    """Test reading random double"""
    value = qrnx.read_double()
    assert isinstance(value, float)
    assert 0.0 <= value < 1.0


def test_read_int_range(qrnx):
    """Test reading random integer in range"""
    for _ in range(10):
        value = qrnx.read_int_range(10, 20)
        assert isinstance(value, int)
        assert 10 <= value <= 20


def test_read_int_range_single_value(qrnx):
    """Test reading random integer when min equals max"""
    value = qrnx.read_int_range(42, 42)
    assert value == 42


def test_read_bytes_list(qrnx):
    """Test reading bytes as list"""
    byte_list = qrnx.read_bytes_list(10)
    assert isinstance(byte_list, list)
    assert len(byte_list) == 10
    assert all(isinstance(b, int) and 0 <= b <= 255 for b in byte_list)


def test_invalid_device_number():
    """Test that invalid device number raises exception"""
    with pytest.raises(QuantixException):
        Quantix(DeviceType.PCI, device_number=999)


def test_usb_not_supported():
    """Test that USB devices are not supported"""
    with pytest.raises(QuantixException):
        Quantix(DeviceType.USB, device_number=0)


def test_read_zero_bytes(qrnx):
    """Test that reading zero bytes raises ValueError"""
    with pytest.raises(ValueError):
        qrnx.read(0)


def test_read_negative_bytes(qrnx):
    """Test that reading negative bytes raises ValueError"""
    with pytest.raises(ValueError):
        qrnx.read(-1)


def test_read_int_range_invalid(qrnx):
    """Test that invalid range raises ValueError"""
    with pytest.raises(ValueError):
        qrnx.read_int_range(20, 10)
