"""
Quantis USB backend for Quantix.

Python port of QuantisUsb_Unix.c / QuantisUsb_Commands.h from ID Quantique's
libQuantis. Uses PyUSB on top of libusb-1.0, the same transport as the C code.
"""

from __future__ import annotations

import errno
import time
from collections.abc import Iterable
from typing import Any, cast

# PyUSB has no inline types. "unused-ignore" keeps this clean even if stubs
# or a mypy override for "usb" are present.
import usb.backend.libusb1  # type: ignore[import-untyped, unused-ignore]
import usb.core  # type: ignore[import-untyped, unused-ignore]
import usb.util  # type: ignore[import-untyped, unused-ignore]

# No import cycle at runtime: quantix.py imports this module lazily.
from .quantix import QuantixException

# ---- QuantisUsb_Commands.h ---------------------------------------------------
VENDOR_ID_ELLISYS = 0x0ABA
DEVICE_ID_QUANTIS_USB = 0x0102

QUANTIS_USB_REQUEST_TIMEOUT = 1000  # ms

QUANTIS_USB_CMD_GET_BOARD_VERSION = 0x10
QUANTIS_USB_CMD_MODULE_DISABLE = 0x11
QUANTIS_USB_CMD_MODULE_ENABLE = 0x12
QUANTIS_USB_CMD_GET_MODULES_STATUS = 0x13
QUANTIS_USB_CMD_GET_MODULES_POWER = 0x14
QUANTIS_USB_CMD_GET_MODULES_MASK = 0x15
QUANTIS_USB_CMD_GET_MODULES_RATE = 0x16
QUANTIS_USB_CMD_GET_AIS31_STARTUP_TESTS_REQUEST_FLAG = 0x17  # defined, not ported
QUANTIS_USB_CMD_CLEAR_AIS31_STARTUP_TESTS_REQUEST_FLAG = 0x18  # defined, not ported

USB_MAX_BULK_PACKET_SIZE = 512  # 64 on USB 1.x, 512 on USB 2.0
QUANTIS_USB_ENDPOINT_BULK_IN = 0x86

# ---- QuantisUsb_Unix.c -------------------------------------------------------
DRIVER_VERSION = 1.0  # "Driver version == libusb version"
NO_SERIAL = "S/N not available"  # placeholder for QUANTIS_NO_SERIAL
NOT_AVAILABLE = "N/A"  # placeholder for QUANTIS_NOT_AVAILABLE

# VENDOR | RECIPIENT_INTERFACE | IN/OUT -> 0xC1 / 0x41
_REQ_IN: int = usb.util.build_request_type(
    usb.util.CTRL_IN, usb.util.CTRL_TYPE_VENDOR, usb.util.CTRL_RECIPIENT_INTERFACE
)
_REQ_OUT: int = usb.util.build_request_type(
    usb.util.CTRL_OUT, usb.util.CTRL_TYPE_VENDOR, usb.util.CTRL_RECIPIENT_INTERFACE
)


def _find_all() -> list[Any]:
    try:
        backend = usb.backend.libusb1.get_backend()
        found = usb.core.find(
            find_all=True,
            idVendor=VENDOR_ID_ELLISYS,
            idProduct=DEVICE_ID_QUANTIS_USB,
            backend=backend,
        )
        # find_all=True yields a lazy generator; enumerate inside the try.
        return [] if found is None else list(cast(Iterable[Any], found))
    except usb.core.NoBackendError as e:
        raise QuantixException(
            "libusb-1.0 not found (sudo apt install libusb-1.0-0)"
        ) from e
    except usb.core.USBError as e:
        raise QuantixException(f"USB enumeration failed: {e}") from e


def count_usb_devices() -> int:
    """Port of QuantisUsbCount()."""
    return len(_find_all())


class QuantisUsbDevice:
    """Port of the QuantisUsb* functions (one instance = one device handle)."""

    device_number: int
    check_status_per_packet: bool
    serial_number: str
    manufacturer: str
    product: str
    _dev: Any
    _candidate: Any
    _max_packet: int

    def __init__(
        self, device_number: int = 0, check_status_per_packet: bool = True
    ) -> None:
        self.device_number = device_number
        # The C code checks the module status before EVERY bulk packet. Faithful,
        # but costs one control transfer per packet. False = check once per read().
        self.check_status_per_packet = check_status_per_packet
        self.serial_number = NO_SERIAL
        self.manufacturer = NOT_AVAILABLE
        self.product = NOT_AVAILABLE
        self._dev = None
        self._max_packet = 0

        devices = _find_all()
        # C uses `count < deviceNumber` (off-by-one); use a proper bounds check.
        if not 0 <= device_number < len(devices):
            raise QuantixException(
                f"Quantis USB device #{device_number} not found "
                f"({len(devices)} present)",
                self.path,
            )
        self._candidate = devices[device_number]

    @property
    def path(self) -> str:
        vid, pid = VENDOR_ID_ELLISYS, DEVICE_ID_QUANTIS_USB
        return f"usb:{vid:04x}:{pid:04x}#{self.device_number}"

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    # ---- open / close --------------------------------------------------------

    def open(self) -> None:
        """Port of QuantisUsbOpen()."""
        if self._dev is not None:
            return
        dev = self._candidate
        try:
            try:
                if dev.is_kernel_driver_active(0):
                    dev.detach_kernel_driver(0)
            except (NotImplementedError, usb.core.USBError):
                pass

            # libusb_set_configuration(handle, 1). Skip if already active
            # (re-setting it triggers a needless lightweight reset on Linux).
            active: int | None
            try:
                active = int(dev.get_active_configuration().bConfigurationValue)
            except usb.core.USBError:
                active = None
            if active != 1:
                dev.set_configuration(1)

            usb.util.claim_interface(dev, 0)
        except usb.core.USBError as e:
            if e.errno == errno.EACCES:
                msg = "permission denied (install the udev rule / join plugdev)"
            elif e.errno == errno.EBUSY:
                msg = "device busy (only one process may use it at a time)"
            else:
                msg = str(e)
            raise QuantixException(
                f"Cannot open {self.path}: {msg}", self.path
            ) from e

        try:
            # Same sanity checks as the C code
            cfg = dev.get_active_configuration()
            if dev.bNumConfigurations != 1 or cfg.bNumInterfaces != 1:
                raise QuantixException(
                    "Unexpected USB configuration layout", self.path
                )
            endpoints = list(cfg[(0, 0)])
            if not endpoints:
                raise QuantixException("Interface 0 has no endpoints", self.path)
            # C takes endpoint[0].wMaxPacketSize; prefer 0x86 explicitly.
            ep = next(
                (
                    x
                    for x in endpoints
                    if x.bEndpointAddress == QUANTIS_USB_ENDPOINT_BULK_IN
                ),
                endpoints[0],
            )
            self._max_packet = int(ep.wMaxPacketSize) & 0x7FF
            if self._max_packet == 0:
                raise QuantixException(
                    "Bulk endpoint reports wMaxPacketSize 0", self.path
                )

            self.serial_number = self._get_string(dev, dev.iSerialNumber, NO_SERIAL)
            self.manufacturer = self._get_string(
                dev, dev.iManufacturer, NOT_AVAILABLE
            )
            self.product = self._get_string(dev, dev.iProduct, NOT_AVAILABLE)
        except Exception:
            self._release(dev)
            raise

        self._dev = dev

    def close(self) -> None:
        """Port of QuantisUsbClose()."""
        dev, self._dev = self._dev, None
        if dev is not None:
            self._release(dev)

    @staticmethod
    def _release(dev: Any) -> None:
        try:
            usb.util.release_interface(dev, 0)
        except Exception:
            pass
        try:
            usb.util.dispose_resources(dev)
        except Exception:
            pass

    @staticmethod
    def _get_string(dev: Any, index: int, fallback: str) -> str:
        if not index:
            return fallback
        try:
            value = usb.util.get_string(dev, index)
        except Exception:
            return fallback
        return str(value) if value else fallback

    # ---- control transfers (QuantisUsbGetIntValue / GetUCHARValue / SendRequest)

    def _require_open(self) -> Any:
        if self._dev is None:
            raise QuantixException(
                "Device is not open. "
                "Use 'with Quantix(...) as qrng:' to open the device.",
                self.path,
            )
        return self._dev

    def _get_value(self, request: int, length: int) -> int:
        dev = self._require_open()
        try:
            data = dev.ctrl_transfer(
                _REQ_IN, request, 0, 0, length, QUANTIS_USB_REQUEST_TIMEOUT
            )
        except usb.core.USBError as e:
            raise QuantixException(
                f"Control request 0x{request:02x} failed: {e}", self.path
            ) from e
        if len(data) != length:
            raise QuantixException(
                f"Control request 0x{request:02x}: got {len(data)}/{length} bytes",
                self.path,
            )
        return int.from_bytes(bytes(data), "little")

    def _send_request(self, request: int) -> None:
        dev = self._require_open()
        try:
            dev.ctrl_transfer(
                _REQ_OUT, request, 0, 0, None, QUANTIS_USB_REQUEST_TIMEOUT
            )
        except usb.core.USBError as e:
            raise QuantixException(
                f"Control request 0x{request:02x} failed: {e}", self.path
            ) from e

    # ---- information ---------------------------------------------------------

    def get_driver_version(self) -> float:
        return DRIVER_VERSION

    def get_board_version(self) -> int:
        return self._get_value(QUANTIS_USB_CMD_GET_BOARD_VERSION, 4)

    def get_modules_mask(self) -> int:
        return self._get_value(QUANTIS_USB_CMD_GET_MODULES_MASK, 1)

    def get_modules_status(self) -> int:
        return self._get_value(QUANTIS_USB_CMD_GET_MODULES_STATUS, 1)

    def get_modules_power(self) -> int:
        return self._get_value(QUANTIS_USB_CMD_GET_MODULES_POWER, 1)

    def get_modules_data_rate(self) -> int:
        """Bytes/s. The device reports kbit/s per module."""
        rate = self._get_value(QUANTIS_USB_CMD_GET_MODULES_RATE, 4) * 1000 // 8
        return rate * bin(self.get_modules_mask()).count("1")

    # ---- control -------------------------------------------------------------

    def modules_enable(self, mask: int) -> None:
        if not mask & 0x1:
            raise ValueError("Quantis USB only has one module (bit 0)")
        self._send_request(QUANTIS_USB_CMD_MODULE_ENABLE)

    def modules_disable(self, mask: int) -> None:
        if not mask & 0x1:
            raise ValueError("Quantis USB only has one module (bit 0)")
        self._send_request(QUANTIS_USB_CMD_MODULE_DISABLE)

    def board_reset(self) -> None:
        """Port of QuantisUsbBoardReset().

        Faithful to C, including its condition: `mask != 0` is true whenever the
        module is present, so in practice the module is always power-cycled.
        """
        if self.get_modules_status() != 0x0001 or self.get_modules_mask() != 0x0000:
            self.modules_disable(0xFFFFFFFF)
            self.modules_enable(0xFFFFFFFF)
            time.sleep(1)
        self.read(4096)  # discard the first 4 KiB after a restart

    # ---- data ----------------------------------------------------------------

    def read(self, size: int) -> bytes:
        """Port of QuantisUsbRead().

        Each bulk request must be exactly wMaxPacketSize; surplus bytes of the
        last packet are discarded (as in C).
        """
        dev = self._require_open()
        pkt = self._max_packet
        out = bytearray()
        while len(out) < size:
            if self.check_status_per_packet or not out:
                if self.get_modules_status() <= 0:
                    raise QuantixException(
                        "Module status not OK (QUANTIS_ERROR_INVALID_STATUS)",
                        self.path,
                    )
            try:
                data = dev.read(
                    QUANTIS_USB_ENDPOINT_BULK_IN, pkt, QUANTIS_USB_REQUEST_TIMEOUT
                )
            except usb.core.USBError as e:
                raise QuantixException(f"Bulk read failed: {e}", self.path) from e
            if len(data) != pkt:
                # C returns `result` (often 0) here, leaving the buffer unfilled.
                raise QuantixException(
                    f"Short bulk read: {len(data)}/{pkt} bytes", self.path
                )
            out += bytes(data[: size - len(out)])
        return bytes(out)

