# CC1101 MicroPython SPI Driver for Raspberry Pi Pico
#
# Minimal driver focused on receiving 868.3 MHz Bresser weather frames.
#
# Notes
# - This is a pragmatic subset of CC1101 functionality for RX only.
# - It configures 2-FSK/GFSK at ~8.2 kbps, 868.3 MHz, fixed-length packets,
#   sync word 0x2D D4 and status bytes appended by CC1101 (RSSI/LQI+CRC_OK).
# - The exact demodulation/AGC/rate/bandwidth settings may need fine tuning
#   using TI SmartRF Studio values for your transceiver. Values included here
#   are known to work with many Bresser 868 MHz sensors but may require
#   adjustment depending on your module and environment.
#
# Hardware wiring (as per env.py defaults):
#   - SPI0: SCK=GP18, MOSI=GP19, MISO=GP16
#   - CSN:  GP17
#   - GDO0: GP20 (optional)
#   - GDO2: GP21 (optional)
#
# Author's template friendly: typed method docstrings and concise API.

# typing is optional on MicroPython; provide a tiny shim for annotations
try:
    from typing import Optional  # type: ignore
except ImportError:  # MicroPython often lacks typing module
    class _TypingShim:
        def __getitem__(self, item):
            return item
    Optional = _TypingShim()  # type: ignore
from machine import SPI, Pin
from time import ticks_ms, ticks_diff, sleep_ms


# Register addresses (see TI CC1101 datasheet)
IOCFG2   = 0x00
IOCFG1   = 0x01
IOCFG0   = 0x02
FIFOTHR  = 0x03
SYNC1    = 0x04
SYNC0    = 0x05
PKTLEN   = 0x06
PKTCTRL1 = 0x07
PKTCTRL0 = 0x08
ADDR     = 0x09
CHANNR   = 0x0A
FSCTRL1  = 0x0B
FSCTRL0  = 0x0C
FREQ2    = 0x0D
FREQ1    = 0x0E
FREQ0    = 0x0F
MDMCFG4  = 0x10
MDMCFG3  = 0x11
MDMCFG2  = 0x12
MDMCFG1  = 0x13
MDMCFG0  = 0x14
DEVIATN  = 0x15
MCSM2    = 0x16
MCSM1    = 0x17
MCSM0    = 0x18
FOCCFG   = 0x19
BSCFG    = 0x1A
AGCTRL2  = 0x1B
AGCTRL1  = 0x1C
AGCTRL0  = 0x1D
WOREVT1  = 0x1E
WOREVT0  = 0x1F
WORCTRL  = 0x20
FREND1   = 0x21
FREND0   = 0x22
FSCAL3   = 0x23
FSCAL2   = 0x24
FSCAL1   = 0x25
FSCAL0   = 0x26
TEST2    = 0x2C
TEST1    = 0x2D
TEST0    = 0x2E

# Status registers
PARTNUM  = 0x30 | 0xC0
VERSION  = 0x31 | 0xC0
RSSI     = 0x34 | 0xC0
MARCSTATE= 0x35 | 0xC0
RXBYTES  = 0x3B | 0xC0

# Command strobes
SRES   = 0x30
SFSTXON= 0x31
SXOFF  = 0x32
SCAL   = 0x33
SRX    = 0x34
STX    = 0x35
SIDLE  = 0x36
SFRX   = 0x3A
SFTX   = 0x3B

READ_SINGLE = 0x80
READ_BURST  = 0xC0
WRITE_BURST = 0x40


class CC1101:
    """
    Minimal CC1101 driver for RX usage.

    Example:
        spi = SPI(0, sck=Pin(18), mosi=Pin(19), miso=Pin(16), baudrate=4000000)
        cs = Pin(17, Pin.OUT)
        radio = CC1101(spi, cs, gdo0=20, gdo2=21, debug=True)
        radio.reset()
        radio.configure_bresser(pkt_len=27)
        radio.enter_rx()
        frame = radio.read_packet(timeout_ms=200)
    """

    # --- Useful constants for RX bandwidth presets (see datasheet) ---
    # BW = f_xtal / (8 * (4 + M) * 2^E) with f_xtal = 26 MHz
    # We define two presets: ~270.8 kHz (E=1,M=2) and ~232.1 kHz (E=1,M=3) as an
    # approximation for "250 kHz" requested when probing.
    _BW_PRESETS = {
        '270k': (1, 2),  # ~270.8 kHz
        '250k': (1, 3),  # ~232.1 kHz (closest available below 250 kHz)
        '100k': (0, 3),  # ~100.4 kHz (not recommended)
    }

    def __init__(self, spi, cs, gdo0=None, gdo2=None, debug=False):
        self.spi = spi
        self.cs = cs if isinstance(cs, Pin) else Pin(cs, Pin.OUT)
        self.debug = debug
        self.gdo0 = Pin(gdo0, Pin.IN) if isinstance(gdo0, int) else gdo0
        self.gdo2 = Pin(gdo2, Pin.IN) if isinstance(gdo2, int) else gdo2
        self.cs.value(1)

    # ---------------------- Low-level SPI ----------------------
    def _select(self):
        self.cs.value(0)

    def _deselect(self):
        self.cs.value(1)

    def strobe(self, cmd: int) -> int:
        """Send a command strobe and return status byte."""
        self._select()
        tx = bytearray([cmd & 0xFF])
        rx = bytearray(1)
        if hasattr(self.spi, 'write_readinto'):
            self.spi.write_readinto(tx, rx)
        else:
            # Best-effort fallback: write only, no status available
            self.spi.write(tx)
            rx[0] = 0
        self._deselect()
        return rx[0]

    def write_reg(self, addr: int, value: int) -> None:
        self._select()
        self.spi.write(bytearray([addr & 0x3F, value & 0xFF]))
        self._deselect()

    def read_reg(self, addr: int) -> int:
        self._select()
        self.spi.write(bytearray([(addr & 0x3F) | READ_SINGLE]))
        rb = self.spi.read(1)
        self._deselect()
        return rb[0] if rb else 0

    def read_status_reg(self, addr: int) -> int:
        """Read a status register (addr must be full status address like 0xC0|reg)."""
        self._select()
        # For status registers, the burst bit should be set even for single read.
        self.spi.write(bytearray([(addr & 0x3F) | READ_BURST]))
        rb = self.spi.read(1)
        self._deselect()
        return rb[0] if rb else 0

    def write_burst(self, addr: int, data: bytes) -> None:
        self._select()
        self.spi.write(bytearray([(addr & 0x3F) | WRITE_BURST]))
        self.spi.write(data)
        self._deselect()

    def get_rssi_dbm (self) -> float:
        """Read RSSI register and convert to dBm."""
        rssi_reg = self.read_status_reg(RSSI)
        if rssi_reg >= 128:  # Negative value
            rssi_dbm = (rssi_reg - 256) / 2.0 - 74
        else:  # Positive value
            rssi_dbm = rssi_reg / 2.0 - 74
        return rssi_dbm

    def read_burst(self, addr: int, length: int) -> bytes:
        self._select()
        self.spi.write(bytearray([(addr & 0x3F) | READ_BURST]))
        rb = self.spi.read(length)
        self._deselect()
        return rb if rb else b""

    # ---------------------- High-level ops ----------------------
    def reset(self) -> None:
        """Perform CC1101 reset sequence."""
        self.cs.value(1)
        sleep_ms(1)
        self.cs.value(0)
        sleep_ms(1)
        self.cs.value(1)
        sleep_ms(1)
        self.strobe(SRES)
        sleep_ms(1)
        # Initialize defaults
        self._bw_profile = '270k'

    def configure_bresser(self, pkt_len: int = 27, strict_sync: bool = False, bw_profile: str = '270k', freq_hz: int = None) -> None:
        """
        Configure the CC1101 for Bresser sensors at ~868 MHz (2-FSK ~8.2 kbps).

        Args:
            pkt_len: Fixed packet length in bytes (no status bytes appended).
            strict_sync: If True uses SYNC=0x2D,0xD4; if False uses 0xAA,0x2D.
            bw_profile: '270k' (default) or '250k' (~232 kHz) RX BW.
            freq_hz: Center frequency in Hz (default 868_300_000 if None).
        """
        # Enter IDLE and flush FIFOs
        self.strobe(SIDLE)
        self.strobe(SFRX)
        self.strobe(SFTX)

        # GDO pins: 0x06 asserts on sync, deasserts end of packet (packet done)
        self.write_reg(IOCFG0, 0x06)
        self.write_reg(IOCFG2, 0x0D)  # High-Z for GDO2 (can be changed)

        # FIFO threshold (default mid)
        self.write_reg(FIFOTHR, 0x07)

        # Sync words:
        # - strict_sync=False (default): "AA 2D" trick — preamble is AA AA AA AA 2D,
        #   then D4 appears as the FIRST BYTE of the 27-byte payload.
        #   The decoder checks packet[0]==0xD4 and uses packet[1:27] as the 26-byte message.
        # - strict_sync=True: exact sync 2D D4, payload starts right after; pkt_len should be 26.
        # BUG FIX: These registers MUST be written. Without them the CC1101 keeps its
        # reset-default sync words (0xD3 0x91) and will never match a Bresser frame.
        if strict_sync:
            self.write_reg(SYNC1, 0x2D)
            self.write_reg(SYNC0, 0xD4)
        else:
            # AA 2D trick (compatible with C project and old Python project)
            self.write_reg(SYNC1, 0xAA)
            self.write_reg(SYNC0, 0x2D)

        # Packet control: no address check, do NOT append status
        # ADR_CHK bits [1:0] = 00 → no address check
        self.write_reg(PKTCTRL1, 0x00)

        # BUG FIX: Use FIXED length mode (0x00), NOT variable (0x02).
        # In variable-length mode the CC1101 reads the first payload byte as the
        # length field. With SYNC=AA 2D the first byte is D4=212, which exceeds
        # PKTLEN=40, so EVERY Bresser packet is silently discarded by hardware.
        # Fixed-length mode reads exactly pkt_len bytes and works correctly.
        #
        # | PKTCTRL0 | Bits     | Configuración                              |
        # | 0x00     | 00000000 | Fixed length, CRC off, no append status    |
        # | 0x02     | 00000010 | Variable length, CRC off, no append status |
        self.write_reg(PKTCTRL0, 0x00)
        self.write_reg(PKTLEN, pkt_len & 0xFF)

        # Frequency control from freq_hz (26 MHz crystal)
        if freq_hz is None:
            # default 868.300 MHz as in old C project
            fword = (868300000 * (1 << 16)) // 26000000
        else:
            try:
                fword = int((int(freq_hz) * (1 << 16)) // 26000000)
            except Exception:
                fword = (868300000 * (1 << 16)) // 26000000
        self.write_reg(FREQ2, (fword >> 16) & 0xFF)
        self.write_reg(FREQ1, (fword >> 8) & 0xFF)
        self.write_reg(FREQ0, fword & 0xFF)

        # Data rate ~8.21 kbps, RX BW preset, 2-FSK, no Manchester
        # MDMCFG4: [7:6]=CHANBW_E, [5:4]=CHANBW_M, [3:0]=DRATE_E
        # Formula: DRATE = (256+DRATE_M) * 2^DRATE_E * 26e6 / 2^28
        # DRATE_E=8, DRATE_M=75 → (256+75)*256*26e6/2^28 = 8,207 bps ✓
        # WARNING: DRATE_E=10 with DRATE_M=131 gives 38,380 bps (was wrong!)
        mdmcfg4 = 0x08  # DRATE_E = 8 → ~8.21 kbps

        # Apply BW preset
        e, m = self._BW_PRESETS.get(bw_profile, self._BW_PRESETS['270k'])
        mdmcfg4 |= ((e & 0x3) << 6) | ((m & 0x3) << 4)
        self.write_reg(MDMCFG4, mdmcfg4)  # result: 0x68 for '270k' profile

        self.write_reg(MDMCFG3, 0x4B)  # DRATE_M=75 → 8,207 bps with DRATE_E=8

        self.write_reg(MDMCFG2, 0x12)  # Sync mode 16/16 bits, 2-FSK, no Manchester (0x13=30/32 is too strict)
        self.write_reg(MDMCFG1, 0x22)  # FEC off, ~4 bytes preamble
        self.write_reg(MDMCFG0, 0xF8)  # Channel spacing (not critical)

        # Frequency deviation ~57.136 kHz
        self.write_reg(DEVIATN, 0x47)
        #self.write_reg(DEVIATN, 0x45)
        #self.write_reg(DEVIATN, 0x76) # Para 250khz? 100k....
        #self.write_reg(DEVIATN, 0x73) # Para 232khz

        # Main state machine config: stay in RX after packet, auto calibrate
        self.write_reg(MCSM0, 0x18)
        self.write_reg(MCSM1, 0x0C)

        # Frequency offset compensation and AGC/bandwidth settings
        self.write_reg(FOCCFG, 0x16)
        self.write_reg(BSCFG,  0x6C)
        self.write_reg(AGCTRL2, 0x07)
        self.write_reg(AGCTRL1, 0x40)
        self.write_reg(AGCTRL0, 0x91)

        # Front-end and calibration
        self.write_reg(FREND1, 0xB6)
        self.write_reg(FREND0, 0x10)
        self.write_reg(FSCAL3, 0xE9)
        self.write_reg(FSCAL2, 0x2A)
        self.write_reg(FSCAL1, 0x00)
        self.write_reg(FSCAL0, 0x1F)

        # Test settings (from SmartRF)
        self.write_reg(TEST2, 0x81)
        self.write_reg(TEST1, 0x31)
        self.write_reg(TEST0, 0x09)

        # Calibrate and enter RX
        self.strobe(SCAL)
        sleep_ms(2)
        self.enter_rx()

    def set_bw_profile(self, bw_profile: str = '270k') -> bool:
        """Set RX bandwidth profile at runtime by updating CHANBW bits in MDMCFG4.
        Performs a quick recalibration and re-enters RX. Returns True on success.
        Profiles:
          - '270k' → ~270.8 kHz
          - '250k' → closest available ~232.1 kHz
          - '100k' -> ~100.4 kHz (not recommended)
        """
        try:
            e, m = self._BW_PRESETS.get(bw_profile, self._BW_PRESETS['270k'])
            cur = self.read_reg(MDMCFG4)
            # Clear CHANBW bits [7:4]
            cur &= 0x0F
            cur |= ((e & 0x3) << 6) | ((m & 0x3) << 4)
            self.write_reg(MDMCFG4, cur)
            # Recalibrate and re-enter RX
            self.strobe(SIDLE)
            self.strobe(SFRX)
            self.strobe(SCAL)
            sleep_ms(2)
            self.strobe(SRX)
            #self._bw_profile = '250k' if (e, m) == self._BW_PRESETS['250k']  else '270k'
            self._bw_profile = (
                '250k' if (e, m) == self._BW_PRESETS['250k']
                else '100k' if (e, m) == self._BW_PRESETS['100k']
                else '270k'
            )

            return True
        except Exception:
            return False

    def enter_rx(self) -> None:
        """Put radio into RX state (flush RX FIFO beforehand)."""
        self.strobe(SIDLE)
        self.strobe(SFRX)
        self.strobe(SRX)

    def ensure_rx(self) -> None:
        """Ensure the radio is in RX and recover from common error states."""
        try:
            marc = self.read_status_reg(MARCSTATE) & 0x1F
            # 0x0D = RX, 0x11 = RXFIFO_OVERFLOW, 0x0F = RX_END
            if marc == 0x11:
                # Overflow: flush and re-enter RX
                self.strobe(SIDLE)
                self.strobe(SFRX)
                self.strobe(SRX)
            elif marc != 0x0D:
                # Not in RX: try to re-enter
                self.strobe(SRX)
        except Exception:
            # Best effort: attempt to re-enter RX
            try:
                self.strobe(SRX)
            except Exception:
                pass

    def rx_bytes_available(self) -> int:
        """Return number of bytes in RX FIFO."""
        val = self.read_status_reg(RXBYTES)
        return val & 0x7F

    def read_fifo(self, length: int) -> bytes:
        """Read 'length' bytes from RX FIFO."""
        # FIFO address for burst reads is 0x3F
        return self.read_burst(0x3F, length)

    def read_packet(self, timeout_ms: int = 100) -> Optional[bytes]:
        """
        Read one packet from RX FIFO.
        - Fixed-length: read exactly PKTLEN bytes (plus status if enabled).
        - Variable-length: return [L | payload(L) (+ status if enabled)], where L is 1..PKTLEN.

        Note: In variable-length mode the returned data includes the leading length byte.
        """
        t0 = ticks_ms()
        try:
            pkt_len_reg = self.read_reg(PKTLEN) & 0xFF
            pktctrl0 = self.read_reg(PKTCTRL0) & 0xFF
            pktctrl1 = self.read_reg(PKTCTRL1) & 0xFF
        except Exception:
            return None
        append_status = (pktctrl1 & 0x04) != 0  # APPEND_STATUS bit
        length_mode = pktctrl0 & 0x03          # 0=fixed, 1=variable, 2=infinite

        # Helper to recover from overflow
        def _recover_overflow():
            self.strobe(SIDLE)
            self.strobe(SFRX)
            self.strobe(SRX)

        # Fixed-length path
        if length_mode == 0x00:
            expected = pkt_len_reg + (2 if append_status else 0)
            while True:
                rxbytes_val = self.read_status_reg(RXBYTES)
                if (rxbytes_val & 0x80) != 0:
                    _recover_overflow()
                    t0 = ticks_ms()
                    continue
                n = rxbytes_val & 0x7F
                if n >= expected:
                    data = self.read_fifo(expected)
                    return data
                if ticks_diff(ticks_ms(), t0) > timeout_ms:
                    return None
                sleep_ms(1)
        # Variable-length path
        elif length_mode == 0x01:
            # Wait for at least one byte (the length)
            while True:
                rxbytes_val = self.read_status_reg(RXBYTES)
                if (rxbytes_val & 0x80) != 0:
                    _recover_overflow()
                    t0 = ticks_ms()
                    continue
                n = rxbytes_val & 0x7F
                if n >= 1:
                    break
                if ticks_diff(ticks_ms(), t0) > timeout_ms:
                    return None
                sleep_ms(1)
            # Read length byte
            length_bytes = self.read_fifo(1)
            if not length_bytes or len(length_bytes) == 0:
                return None
            L = length_bytes[0]
            # Validate length (1..PKTLEN)
            if L == 0 or L > pkt_len_reg:
                # Invalid length -> flush
                _recover_overflow()
                return None
            expected_payload = L
            expected_total = expected_payload + (2 if append_status else 0)
            # Wait until full payload (and optional status) is available
            while True:
                rxbytes_val = self.read_status_reg(RXBYTES)
                if (rxbytes_val & 0x80) != 0:
                    _recover_overflow()
                    t0 = ticks_ms()
                    # Start over: we lost this packet
                    return None
                n = rxbytes_val & 0x7F
                if n >= expected_total:
                    data = self.read_fifo(expected_total)
                    return data  # payload [+ status]
                if ticks_diff(ticks_ms(), t0) > timeout_ms:
                    # Timeout: flush partial and recover
                    _recover_overflow()
                    return None
                sleep_ms(1)
        else:
            # Infinite length or unsupported: best effort, read whatever is there up to max
            while True:
                rxbytes_val = self.read_status_reg(RXBYTES)
                if (rxbytes_val & 0x80) != 0:
                    _recover_overflow()
                    t0 = ticks_ms()
                    continue
                n = rxbytes_val & 0x7F
                if n > 0:
                    data = self.read_fifo(n)
                    return data
                if ticks_diff(ticks_ms(), t0) > timeout_ms:
                    return None
                sleep_ms(1)

    def get_status(self) -> dict:
        """Return a small dict with PARTNUM, VERSION, MARCSTATE, RSSI and RXBYTES/PKTLEN and key demod regs."""
        try:
            rxbytes_val = self.read_status_reg(RXBYTES)
        except Exception:
            rxbytes_val = 0
        try:
            mdmcfg4 = self.read_reg(MDMCFG4)
            mdmcfg3 = self.read_reg(MDMCFG3)
            mdmcfg2 = self.read_reg(MDMCFG2)
            deviatn = self.read_reg(DEVIATN)
            foccfg = self.read_reg(FOCCFG)
        except Exception:
            mdmcfg4 = mdmcfg3 = mdmcfg2 = deviatn = foccfg = 0
        return {
            "partnum": self.read_status_reg(PARTNUM),
            "version": self.read_status_reg(VERSION),
            "marcstate": self.read_status_reg(MARCSTATE),
            "rssi": self.read_status_reg(RSSI),
            "rssi_dbm": self.get_rssi_dbm(),
            "rxbytes": rxbytes_val & 0x7F,
            "overflow": 1 if (rxbytes_val & 0x80) else 0,
            "pklen": self.read_reg(PKTLEN),
            "mdmcfg4": mdmcfg4,
            "mdmcfg3": mdmcfg3,
            "mdmcfg2": mdmcfg2,
            "deviatn": deviatn,
            "foccfg": foccfg,
        }
