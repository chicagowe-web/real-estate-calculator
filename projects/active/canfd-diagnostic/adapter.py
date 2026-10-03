"""USB CAN FD Adapter Detection and Initialization.

Supports: PEAK PCAN-USB, Vector VN*, generic candlelight firmware.
Phase 1: Hardware driver layer with auto-detection and error recovery.

This module provides hardware-agnostic CAN adapter detection and initialization.
Auto-detection tries adapters in order of preference:
  1. PEAK PCAN-USB (Windows/Linux with pcan driver)
  2. Vector CAN interface (Windows/Linux with VN driver)
  3. socketcan (Linux kernel driver, generic fallback)

Examples:
    Auto-detect and connect to available USB CAN adapter:
    >>> adapter = CANAdapter.detect()
    >>> if adapter.connect():
    ...     msg = can.Message(arbitration_id=0x7DF, data=[0x02, 0x01, 0x05, 0, 0, 0, 0, 0])
    ...     adapter.send(msg)
    ...     response = adapter.recv(timeout=1.0)
    ...     adapter.disconnect()

    Explicit socketcan adapter (Linux):
    >>> adapter = adapter_from_socketcan("can0")
    >>> adapter.connect()

    Connection with retry on Linux socketcan:
    >>> adapter = adapter_from_socketcan("can1")
    >>> success = adapter.connect(retries=3, retry_delay=0.5)
"""

from typing import Optional, List, Tuple
import logging
import platform
import sys
import time
import can

logger = logging.getLogger(__name__)


class AdapterConfig:
    """CAN adapter configuration.

    Attributes:
        bustype: CAN interface type ('socketcan', 'pcan', 'vector')
        channel: CAN channel/interface identifier
        bitrate: CAN bitrate in bps (default 500000 for OBD-II)
        fd: Enable CAN FD mode (default True)
        timeout: Receive timeout in seconds (default 1.0)
    """

    def __init__(
        self,
        bustype: str,
        channel: str,
        bitrate: int = 500000,
        fd: bool = True,
        timeout: float = 1.0
    ):
        self.bustype = bustype
        self.channel = channel
        self.bitrate = bitrate
        self.fd = fd
        self.timeout = timeout

    def __repr__(self) -> str:
        return f"AdapterConfig({self.bustype}, {self.channel}, {self.bitrate}bps, fd={self.fd})"


class CANAdapter:
    """USB CAN Adapter interface with auto-detection and error recovery.

    Supports PEAK PCAN, Vector CAN, and socketcan adapters with automatic
    fallback and platform-aware detection (Windows/Linux).

    Examples:
        Auto-detect and connect:
        >>> adapter = CANAdapter.detect()
        >>> adapter.connect()

        Auto-detect with retry on connection failure:
        >>> adapter = CANAdapter.detect()
        >>> adapter.connect(retries=3, retry_delay=0.5)

        Explicit configuration:
        >>> config = AdapterConfig('socketcan', 'can0', bitrate=500000)
        >>> adapter = CANAdapter(config)
        >>> adapter.connect()
    """

    def __init__(self, config: AdapterConfig):
        self.config = config
        self.bus: Optional[can.BusABC] = None
        self.is_connected = False

    def connect(self, retries: int = 1, retry_delay: float = 0.1) -> bool:
        """Connect to USB CAN adapter with automatic retry.

        Args:
            retries: Number of connection attempts (default 1)
            retry_delay: Delay in seconds between retries (default 0.1)

        Returns:
            True if connected, False if all retries exhausted.

        Raises:
            None - all exceptions are logged and handled gracefully.

        Examples:
            Connect with retries for unreliable adapters:
            >>> adapter = CANAdapter.detect()
            >>> success = adapter.connect(retries=3, retry_delay=0.5)
        """
        for attempt in range(max(1, retries)):
            try:
                self.bus = can.interface.Bus(
                    bustype=self.config.bustype,
                    channel=self.config.channel,
                    bitrate=self.config.bitrate,
                    fd=self.config.fd
                )
                self.is_connected = True
                logger.info(f"Connected to CAN: {self.config.channel} @ {self.config.bitrate}bps")
                return True
            except Exception as e:
                if attempt < max(1, retries) - 1:
                    logger.warning(f"CAN connection attempt {attempt+1}/{retries} failed: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"CAN connection failed after {retries} attempts: {e}")
        return False
    
    def disconnect(self) -> None:
        """Disconnect from CAN bus gracefully.

        Examples:
            >>> adapter = CANAdapter.detect()
            >>> adapter.connect()
            >>> adapter.recv()
            >>> adapter.disconnect()
        """
        if self.bus:
            try:
                self.bus.shutdown()
                logger.info(f"Disconnected from CAN: {self.config.channel}")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self.is_connected = False
        else:
            self.is_connected = False
    
    def send(self, msg: can.Message) -> bool:
        """Send CAN message to the bus.

        Args:
            msg: python-can Message object with arbitration_id and data

        Returns:
            True if sent successfully, False otherwise.

        Examples:
            Send OBD-II Mode 01 (live data) request for PID 0x05 (coolant temp):
            >>> msg = can.Message(
            ...     arbitration_id=0x7DF,
            ...     data=[0x02, 0x01, 0x05, 0, 0, 0, 0, 0]
            ... )
            >>> adapter.send(msg)
            True
        """
        if not self.is_connected or not self.bus:
            logger.warning("Send failed: not connected to CAN bus")
            return False
        try:
            self.bus.send(msg)
            logger.debug(f"[TX] {msg.arbitration_id:03X} {msg.data.hex()}")
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False

    def recv(self, timeout: Optional[float] = None) -> Optional[can.Message]:
        """Receive CAN message from the bus.

        Args:
            timeout: Receive timeout in seconds (uses config.timeout if not specified)

        Returns:
            can.Message if received, None on timeout or error.

        Examples:
            Receive response to OBD-II query:
            >>> msg = adapter.recv(timeout=1.0)
            >>> if msg and 0x7E8 <= msg.arbitration_id <= 0x7EF:
            ...     print(f"Response: {msg.data.hex()}")
        """
        if not self.is_connected or not self.bus:
            logger.warning("Recv failed: not connected to CAN bus")
            return None
        try:
            msg = self.bus.recv(timeout=timeout or self.config.timeout)
            if msg:
                logger.debug(f"[RX] {msg.arbitration_id:03X} {msg.data.hex()}")
            return msg
        except Exception as e:
            logger.error(f"Recv failed: {e}")
            return None
    
    @staticmethod
    def detect() -> 'CANAdapter':
        """Auto-detect available USB CAN adapter.

        Detection order (platform-aware):
        1. PEAK PCAN-USB (via pcan driver)
        2. Vector CAN (via VN driver)
        3. socketcan (Linux kernel CAN, generic fallback)

        Returns:
            CANAdapter instance configured for first available adapter.
            Defaults to socketcan if no USB adapters found.

        Examples:
            >>> adapter = CANAdapter.detect()
            >>> print(adapter.config)
            AdapterConfig(socketcan, can0, 500000bps, fd=True)

            Platform detection:
            >>> import platform
            >>> print(f"Platform: {platform.system()}")  # Windows or Linux
            >>> adapter = CANAdapter.detect()
        """
        system = platform.system()
        logger.info(f"Auto-detecting CAN adapter on {system}...")

        # Try PEAK PCAN first (supports both Windows and Linux)
        pcan_adapter = CANAdapter._detect_pcan()
        if pcan_adapter:
            logger.info(f"Detected PEAK PCAN adapter: {pcan_adapter.config}")
            return pcan_adapter

        # Try Vector next (supports both Windows and Linux)
        vector_adapter = CANAdapter._detect_vector()
        if vector_adapter:
            logger.info(f"Detected Vector CAN adapter: {vector_adapter.config}")
            return vector_adapter

        # Fall back to socketcan (Linux kernel CAN)
        socketcan_adapter = CANAdapter._detect_socketcan()
        if socketcan_adapter:
            logger.info(f"Using socketcan fallback: {socketcan_adapter.config}")
            return socketcan_adapter

        # Last resort: return generic socketcan adapter (may not be available)
        logger.warning("No USB adapters detected. Using socketcan (can0) as fallback.")
        config = AdapterConfig(bustype="socketcan", channel="can0")
        return CANAdapter(config)

    @staticmethod
    def _detect_pcan() -> Optional['CANAdapter']:
        """Detect PEAK PCAN-USB adapter.

        Supports Windows and Linux with pcan driver installed.

        Returns:
            CANAdapter if PCAN found, None otherwise.
        """
        try:
            # Try to open PCAN interface
            import can.interfaces.pcan as pcan_mod

            # Check if PCAN hardware is available
            # PCAN channels typically: PCAN_USBCH1, PCAN_USBCH2, etc.
            for channel in ["PCAN_USBCH1", "PCAN_USBCH2", "PCAN_USBCH3"]:
                try:
                    test_bus = can.interface.Bus(bustype="pcan", channel=channel, bitrate=500000)
                    test_bus.shutdown()
                    config = AdapterConfig(bustype="pcan", channel=channel)
                    logger.debug(f"PCAN adapter available on {channel}")
                    return CANAdapter(config)
                except Exception:
                    continue
            return None
        except ImportError:
            logger.debug("PCAN driver not available")
            return None
        except Exception as e:
            logger.debug(f"PCAN detection failed: {e}")
            return None

    @staticmethod
    def _detect_vector() -> Optional['CANAdapter']:
        """Detect Vector CAN adapter (VN1630, VN1640, etc.).

        Supports Windows and Linux with Vector driver installed.

        Returns:
            CANAdapter if Vector adapter found, None otherwise.
        """
        try:
            # Try to open Vector interface
            import can.interfaces.vector as vector_mod

            # Try standard Vector channel names
            for channel in ["0", "1", "2"]:
                try:
                    test_bus = can.interface.Bus(bustype="vector", channel=channel, bitrate=500000)
                    test_bus.shutdown()
                    config = AdapterConfig(bustype="vector", channel=channel)
                    logger.debug(f"Vector adapter available on channel {channel}")
                    return CANAdapter(config)
                except Exception:
                    continue
            return None
        except ImportError:
            logger.debug("Vector driver not available")
            return None
        except Exception as e:
            logger.debug(f"Vector detection failed: {e}")
            return None

    @staticmethod
    def _detect_socketcan() -> Optional['CANAdapter']:
        """Detect socketcan adapter (Linux kernel CAN).

        Checks for standard CAN interfaces: can0, can1, can2

        Returns:
            CANAdapter if socketcan found, None otherwise.
        """
        if platform.system() != "Linux":
            logger.debug("socketcan is Linux-only, skipping on this platform")
            return None

        try:
            # Check for standard CAN interface files
            import os
            for channel in ["can0", "can1", "can2", "can3"]:
                if os.path.exists(f"/sys/class/net/{channel}"):
                    try:
                        # Verify interface is working
                        test_bus = can.interface.Bus(bustype="socketcan", channel=channel, bitrate=500000)
                        test_bus.shutdown()
                        config = AdapterConfig(bustype="socketcan", channel=channel)
                        logger.debug(f"socketcan adapter available: {channel}")
                        return CANAdapter(config)
                    except Exception as e:
                        logger.debug(f"socketcan {channel} check failed: {e}")
                        continue
            return None
        except Exception as e:
            logger.debug(f"socketcan detection failed: {e}")
            return None


def adapter_from_socketcan(channel: str = "can0") -> CANAdapter:
    """Create socketcan adapter (Linux kernel CAN, generic fallback).

    socketcan is the recommended Linux CAN interface. All USB CAN adapters
    on Linux should present as socketcan interfaces.

    Args:
        channel: CAN interface name (default "can0")

    Returns:
        CANAdapter configured for socketcan

    Raises:
        None - raises are handled by connect() method

    Examples:
        Create socketcan adapter for can0:
        >>> adapter = adapter_from_socketcan("can0")
        >>> adapter.connect()

        Use with retry for unreliable connections:
        >>> adapter = adapter_from_socketcan("can1")
        >>> success = adapter.connect(retries=3, retry_delay=0.5)
    """
    config = AdapterConfig(bustype="socketcan", channel=channel)
    return CANAdapter(config)
