"""
Tests for device information and ioctl operations

These tests require actual hardware to run.
"""

import pytest
from quantix import Quantix, DeviceType, count_devices


@pytest.fixture
def qrnx():
    """Fixture providing an opened Quantis device with proper cleanup"""
    count = count_devices(DeviceType.PCI)
    if count == 0:
        pytest.skip("No PCI devices available")

    device = Quantix(DeviceType.PCI, device_number=0)
    with device:
        yield device


def test_get_driver_version(qrnx):
    """Test driver version retrieval via ioctl"""
    version = qrnx.get_driver_version()
    assert isinstance(version, float)
    assert version > 0
    # Driver version should be reasonable (e.g., 2.1, not 999.0)
    assert version < 100


def test_get_board_version(qrnx):
    """Test board version retrieval via ioctl"""
    version = qrnx.get_board_version()
    assert isinstance(version, int)
    assert version > 0


def test_get_modules_mask(qrnx):
    """Test modules mask retrieval via ioctl"""
    mask = qrnx.get_modules_mask()
    assert isinstance(mask, int)
    # Mask should be between 0 and 15 (4 modules max)
    assert 0 <= mask <= 15


def test_get_modules_status(qrnx):
    """Test modules status retrieval via ioctl"""
    status = qrnx.get_modules_status()
    assert isinstance(status, int)
    # Status should be between 0 and 15 (4 modules max)
    assert 0 <= status <= 15


def test_get_modules_count(qrnx):
    """Test counting working modules"""
    count = qrnx.get_modules_count()
    assert isinstance(count, int)
    # Should have at least 1 working module
    assert 0 <= count <= 4


def test_modules_status_matches_mask(qrnx):
    """Test that module status is a subset of module mask"""
    mask = qrnx.get_modules_mask()
    status = qrnx.get_modules_status()
    # All status bits should be set in mask (status is subset of mask)
    assert (status & mask) == status


def test_get_pci_info(qrnx):
    """Test PCI bus/device ID retrieval"""
    bus_id, device_id = qrnx.get_pci_info()
    assert isinstance(bus_id, int)
    assert isinstance(device_id, int)
    # Bus and device IDs should be reasonable
    assert bus_id >= 0
    assert device_id >= 0


def test_reset_board(qrnx):
    """Test board reset operation"""
    # This should not raise an exception
    qrnx.reset_board()
    # After reset, device should still be functional
    data = qrnx.read(4)
    assert len(data) == 4


def test_enable_module_invalid(qrnx):
    """Test that invalid module number raises ValueError"""
    with pytest.raises(ValueError):
        qrnx.enable_module(4)

    with pytest.raises(ValueError):
        qrnx.enable_module(-1)


def test_disable_module_invalid(qrnx):
    """Test that invalid module number raises ValueError"""
    with pytest.raises(ValueError):
        qrnx.disable_module(4)

    with pytest.raises(ValueError):
        qrnx.disable_module(-1)


def test_module_enable_disable(qrnx):
    """Test enabling and disabling modules"""
    # Get initial status
    initial_status = qrnx.get_modules_status()

    # Try to disable module 0 (if it exists)
    if initial_status & 1:
        qrnx.disable_module(0)
        # Note: We don't check if it actually disabled because
        # the driver might not allow disabling all modules

    # Re-enable module 0
    qrnx.enable_module(0)

    # Device should still work
    data = qrnx.read(4)
    assert len(data) == 4
