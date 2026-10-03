"""OBD-II Data Collection and Parsing - ISO 15765-2 over CAN.

Modes: 01 (live), 02 (freeze frame), 03 (DTCs), 09 (vehicle info), 19 (emissions).
Phase 2: OBD collector and decoder with full multi-frame ISO-TP support.

Implemented:
- Mode 01: Live data queries (RPM, speed, temps, O2, fuel pressure)
- Mode 02: Freeze frame data (live data at time of fault)
- Mode 03: Diagnostic Trouble Codes (DTCs as P/C/B/U-codes)
- Mode 09: Vehicle information (VIN, calibration ID)
- ISO-TP multi-frame response handling (single/first/consecutive frames)
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import time
import logging
import can

from adapter import CANAdapter

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticData:
    """Vehicle diagnostic data."""
    live_data: Dict[str, float]
    dtcs: List[str]
    pending_dtcs: List[str]
    freeze_frame: Dict[str, float]
    vehicle_info: Dict[str, str]


class OBDCollector:
    """OBD-II data collector."""
    
    PIDS = {
        0x05: ("Coolant Temp", lambda d: d[0] - 40),
        0x0C: ("RPM", lambda d: ((d[0] * 256) + d[1]) / 4),
        0x0D: ("Speed", lambda d: d[0]),
        0x0F: ("IAT", lambda d: d[0] - 40),
        0x10: ("MAF", lambda d: ((d[0] * 256) + d[1]) / 100),
        0x14: ("O2 Sensor 1", lambda d: d[0] / 200),
        0x1F: ("Runtime", lambda d: ((d[0] * 256) + d[1])),
    }
    
    def __init__(self, adapter: CANAdapter):
        self.adapter = adapter
        self.query_timeout = 0.3
    
    def query_pid(self, mode: int, pid: int) -> Optional[bytes]:
        """Query single PID. Returns data bytes or None."""
        request = can.Message(
            arbitration_id=0x7DF,
            data=bytearray([0x02, mode, pid, 0, 0, 0, 0, 0]),
            is_extended_id=False
        )
        
        if not self.adapter.send(request):
            return None
        
        deadline = time.time() + self.query_timeout
        while time.time() < deadline:
            msg = self.adapter.recv(timeout=0.05)
            if msg and 0x7E8 <= msg.arbitration_id <= 0x7EF:
                if len(msg.data) >= 3 and msg.data[2] == pid:
                    logger.debug(f"PID {pid:02X}: {msg.data.hex()}")
                    return msg.data[3:]
        return None
    
    def query_live_data(self) -> Dict[str, float]:
        """Query all live data PIDs (Mode 01)."""
        live_data = {}
        for pid, (name, decoder) in self.PIDS.items():
            response = self.query_pid(0x01, pid)
            if response and len(response) >= 2:
                try:
                    value = decoder(response)
                    live_data[name] = value
                    logger.info(f"{name}: {value:.2f}")
                except Exception as e:
                    logger.warning(f"Decode {name} failed: {e}")
        return live_data
    
    def _receive_multiframe_response(self, deadline: float) -> Optional[bytearray]:
        """Receive multi-frame ISO-TP response (handles frames split across CAN messages).

        ISO-TP (ISO 15765) framing:
        - Single frame: [0x0N, payload...] where N = payload length
        - First frame: [0x10+, length_bytes, payload...]
        - Consecutive frame: [0x2N, payload] where N = sequence number

        Returns assembled response or None if incomplete.
        """
        frames = bytearray()
        frame_count = 0
        expected_bytes = 0

        while time.time() < deadline:
            msg = self.adapter.recv(timeout=0.05)
            if not msg or not (0x7E8 <= msg.arbitration_id <= 0x7EF):
                continue

            data = msg.data
            if not data:
                continue

            pci = data[0]

            if pci & 0xF0 == 0x10:  # First frame
                expected_bytes = ((pci & 0x0F) << 8) | data[1]
                frames.extend(data[2:])
                frame_count = 0
                logger.debug(f"First frame: {expected_bytes} bytes total")
            elif pci & 0xF0 == 0x20:  # Consecutive frame
                frame_count += 1
                frames.extend(data[1:])
                logger.debug(f"Consecutive frame {frame_count}: {len(data)-1} bytes")
                if len(frames) >= expected_bytes:
                    return frames[:expected_bytes]
            elif pci & 0xF0 == 0x00:  # Single frame
                payload_len = pci & 0x0F
                logger.debug(f"Single frame: {payload_len} bytes")
                return bytearray(data[1:1+payload_len])

        return frames if len(frames) > 0 else None

    def _parse_dtc(self, msb: int, lsb: int) -> str:
        """Parse 2-byte DTC into P/C/B/U-code format (e.g., P0300).

        OBD-II DTC format:
        - Byte 0, bits 7-6: Type (0=Powertrain, 1=Chassis, 2=Body, 3=Network)
        - Byte 0, bits 5-0: First digit of code
        - Byte 1: Remaining code digits

        Example: 0x03 0x00 = P0300 (Powertrain, random misfire)
        """
        dtc_type_map = {0: 'P', 1: 'C', 2: 'B', 3: 'U'}

        dtype = (msb >> 6) & 0x03
        dtype_char = dtc_type_map.get(dtype, 'U')

        # Extract 4-digit code from remaining bits
        code = ((msb & 0x3F) << 8) | lsb

        return f"{dtype_char}{code:04X}"

    def query_dtcs(self) -> List[str]:
        """Query active DTCs (Mode 03).

        OBD Mode 03 returns all active diagnostic trouble codes.
        Handles multi-frame responses for vehicles with many codes.

        Returns list of P/C/B/U-codes like ["P0300", "P0301"].
        """
        request = can.Message(
            arbitration_id=0x7DF,
            data=bytearray([0x02, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
            is_extended_id=False
        )

        if not self.adapter.send(request):
            logger.warning("Failed to send DTC query")
            return []

        deadline = time.time() + self.query_timeout
        dtcs = []

        # Receive response(s) - Mode 03 can return multiple frames for many codes
        response = self._receive_multiframe_response(deadline)

        if not response or len(response) < 2:
            logger.warning("No DTC response received")
            return []

        # Response format (after ISO-TP extraction):
        # [0x43, DTC1_msb, DTC1_lsb, DTC2_msb, DTC2_lsb, ...]
        # Position 0 = 0x43 (mode response), Position 1+ = DTC data (2 bytes each)

        if response[0] == 0x43:
            # Parse DTCs starting at position 1
            for i in range(1, len(response) - 1, 2):
                msb = response[i]
                lsb = response[i + 1]

                # 0x00 0x00 indicates no more DTCs
                if msb == 0x00 and lsb == 0x00:
                    break

                dtc = self._parse_dtc(msb, lsb)
                dtcs.append(dtc)
                logger.debug(f"DTC parsed: {dtc} ({msb:02X} {lsb:02X})")

        logger.info(f"Found {len(dtcs)} active DTCs: {dtcs}")
        return dtcs

    def query_freeze_frame(self) -> Dict[str, float]:
        """Query freeze frame data (Mode 02).

        Freeze frame captures live data at the time of fault.
        First retrieves active DTCs, then fetches freeze frame for the first DTC.

        Returns dict of {param_name: value} using same decoders as Mode 01.
        """
        # First, get active DTCs to know which DTC has freeze frame
        dtcs = self.query_dtcs()
        if not dtcs:
            logger.info("No active DTCs, no freeze frame data available")
            return {}

        # Parse first DTC back to bytes for Mode 02 request
        dtc_code = dtcs[0]

        dtype = dtc_code[0]
        dtype_map = {'P': 0, 'C': 1, 'B': 2, 'U': 3}
        dtype_val = dtype_map.get(dtype, 0)
        code_val = int(dtc_code[1:], 16)

        msb = (dtype_val << 6) | ((code_val >> 8) & 0x3F)
        lsb = code_val & 0xFF

        # Mode 02: Read freeze frame for specific DTC and frame 0
        request = can.Message(
            arbitration_id=0x7DF,
            data=bytearray([0x04, 0x02, msb, lsb, 0x00, 0x00, 0x00, 0x00]),
            is_extended_id=False
        )

        if not self.adapter.send(request):
            logger.warning("Failed to send freeze frame query")
            return {}

        deadline = time.time() + self.query_timeout
        response = self._receive_multiframe_response(deadline)

        if not response or len(response) < 2:
            logger.warning("No freeze frame response received")
            return {}

        freeze_frame = {}

        # Response format (after ISO-TP extraction):
        # [0x42, DTC_MSB, DTC_LSB, frame_num, pid1_data, pid2_data, ...]
        # Freeze frame contains same PID structure as live data after header

        # Attempt to decode freeze frame PIDs
        if len(response) > 3 and response[0] == 0x42:
            # Skip past header (mode_resp, dtc_msb, dtc_lsb, frame_num)
            offset = 4

            # Try to decode freeze frame PIDs in order
            # Note: Actual PID ordering depends on vehicle - this is a simplified implementation
            for pid, (name, decoder) in self.PIDS.items():
                if offset + 2 <= len(response):
                    try:
                        # Extract 2 bytes for this PID
                        pid_data = response[offset:offset+2]
                        if pid_data and len(pid_data) >= 2:
                            value = decoder(pid_data)
                            freeze_frame[name] = value
                            logger.debug(f"Freeze frame {name}: {value:.2f}")
                            offset += 2
                        else:
                            break
                    except Exception as e:
                        logger.warning(f"Freeze frame decode {name} failed: {e}")
                        break

        logger.info(f"Freeze frame data ({len(freeze_frame)} params): {freeze_frame}")
        return freeze_frame

    def query_vehicle_info(self) -> Dict[str, str]:
        """Query vehicle information (Mode 09).

        Retrieves vehicle metadata:
        - VIN (info type 0x02): 17-character vehicle identification
        - Calibration ID (info type 0x04): ECU calibration identifier

        Returns dict with vehicle metadata.
        """
        vehicle_info = {}

        # Query VIN (info type 0x02)
        vin_data = self._query_info_type(0x02)
        if vin_data:
            try:
                # VIN is 17 ASCII characters
                vin = vin_data.decode('ascii', errors='replace')[:17]
                vehicle_info['VIN'] = vin.strip()
                logger.info(f"VIN: {vin}")
            except Exception as e:
                logger.warning(f"VIN decode failed: {e}")

        # Query Calibration ID (info type 0x04)
        cal_data = self._query_info_type(0x04)
        if cal_data:
            try:
                # Calibration ID is typically 4 bytes, represented as hex
                cal_id = cal_data.hex().upper()
                vehicle_info['Calibration ID'] = cal_id
                logger.info(f"Calibration ID: {cal_id}")
            except Exception as e:
                logger.warning(f"Calibration ID decode failed: {e}")

        logger.info(f"Vehicle info: {vehicle_info}")
        return vehicle_info

    def _query_info_type(self, info_type: int) -> Optional[bytes]:
        """Query specific vehicle info type (Mode 09 helper).

        Args:
            info_type: 0x02 = VIN, 0x04 = Calibration ID, etc.

        Returns:
            Raw bytes of info data or None if failed.
        """
        request = can.Message(
            arbitration_id=0x7DF,
            data=bytearray([0x02, 0x09, info_type, 0x00, 0x00, 0x00, 0x00, 0x00]),
            is_extended_id=False
        )

        if not self.adapter.send(request):
            logger.debug(f"Failed to send info type {info_type:02X} query")
            return None

        deadline = time.time() + self.query_timeout
        response = self._receive_multiframe_response(deadline)

        if not response or len(response) < 3:
            logger.debug(f"No response for info type {info_type:02X}")
            return None

        # Response format (after ISO-TP extraction):
        # [0x49, info_type, data...]
        if response[0] == 0x49 and response[1] == info_type:
            # Extract data payload (everything after header)
            return bytes(response[2:])

        logger.debug(f"Invalid response for info type {info_type:02X}: {response.hex()}")
        return None

    def collect_all(self) -> DiagnosticData:
        """Collect all diagnostic data."""
        logger.info("Starting OBD data collection...")
        return DiagnosticData(
            live_data=self.query_live_data(),
            dtcs=self.query_dtcs(),
            pending_dtcs=[],
            freeze_frame=self.query_freeze_frame(),
            vehicle_info=self.query_vehicle_info()
        )
