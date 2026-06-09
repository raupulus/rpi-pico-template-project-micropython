# WeatherSensor model for Raspberry Pi Pico + CC1101 (MicroPython)
#
# This class wraps the CC1101 radio to receive Bresser 868 MHz weather sensor
# frames. It provides typed, well-documented methods and a clear separation of
# responsibilities for easy integration with the template project.
#
# Decoding notes:
# - Full Bresser 5-in-1/6-in-1 frame decoding is non-trivial and includes
#   parity/CRC checks and bitfield parsing. Here we provide a clean interface
#   and a minimal decoder stub you can extend. Refer to the original C project
#   in old_c_project/src/WeatherSensor.cpp for authoritative decoding logic.
# - The driver is configured for fixed-length 27-byte payloads, as in the C
#   project. Two extra status bytes (RSSI, LQI/CRC_OK) are appended by CC1101.

try:
    from typing import Optional, Dict, Any
except ImportError:  # MicroPython often lacks typing module
    class _TypingShim:
        def __getitem__(self, item):
            # Allow annotations like Optional[T] or Dict[K, V] to be evaluated
            return item
    Optional = _TypingShim()  # type: ignore
    Dict = _TypingShim()      # type: ignore
    Any = object              # type: ignore
from binascii import hexlify
# sleep_ms compat for MicroPython/CPython tools
try:
    from time import sleep_ms  # type: ignore
except Exception:  # pragma: no cover - desktop tools
    try:
        from utime import sleep_ms  # type: ignore
    except Exception:
        def sleep_ms(_ms):
            return None

# Opciones desde env.py (si existe)
try:
    import env as _env
    _SENSOR_INC = set(getattr(_env, 'SENSOR_IDS_INC', []) or [])
    _SENSOR_EXC = set(getattr(_env, 'SENSOR_IDS_EXC', []) or [])
    _DECODE_DEBUG = bool(getattr(_env, 'DECODE_DEBUG', False))
    _FIND_ID_STRICT = bool(getattr(_env, 'FIND_ID_STRICT', False))
    _ALLOW_SLIDING_DECODE = bool(getattr(_env, 'ALLOW_SLIDING_DECODE', False))
except Exception:
    _SENSOR_INC = set()
    _SENSOR_EXC = set()
    _DECODE_DEBUG = False
    _FIND_ID_STRICT = False
    _ALLOW_SLIDING_DECODE = False

try:
    from Drivers.CC1101 import CC1101
except ImportError:
    # Allow running static tools outside MicroPython
    CC1101 = None  # type: ignore


class WeatherSensor:
    """
    High-level radio wrapper to receive Bresser weather frames using a CC1101.

    Usage:
        from machine import Pin
        from machine import SPI
        # Create SPI via RpiPico helper or directly
        # spi = SPI(0, sck=Pin(18), mosi=Pin(19), miso=Pin(16), baudrate=4000000)
        # cs = Pin(17, Pin.OUT)
        # ws = WeatherSensor(spi=spi, cs=cs, gdo0=20, gdo2=21, debug=True)
        # ws.begin()
        # pkt = ws.receive(timeout_ms=200)
        # if pkt:
        #     print(ws.decode(pkt))
    """

    def __init__(self, spi, cs, gdo0: Optional[int] = None, gdo2: Optional[int] = None, debug: bool = False):
        self.spi = spi
        self.cs = cs
        self.gdo0 = gdo0
        self.gdo2 = gdo2
        self.debug = debug
        self.radio: Optional[CC1101] = None
        # Longitud base
        self._base_pkt_len = 27
        # Perfil de ancho de banda RX del CC1101 ('270k' por defecto, '250k' como alternativo)
        try:
            import env as _env2
            self._bw_profile = getattr(_env2, 'CC1101_BW_DEFAULT', '270k') or '270k'
            self._freq_hz = int(getattr(_env2, 'CC1101_FREQ_HZ', 868000000) or 868000000)
        except Exception:
            self._bw_profile = '270k'
            self._freq_hz = 868000000

    def begin(self, pkt_len: int = 27) -> bool:
        """
        Initialize CC1101 and enter RX mode.

        Args:
            pkt_len: Fixed packet length expected from sensor (default 27).

        Returns:
            True on success.
        """
        if CC1101 is None:
            return False
        try:
            self.radio = CC1101(self.spi, self.cs, gdo0=self.gdo0, gdo2=self.gdo2, debug=self.debug)
            self.radio.reset()
            # Ajustar longitud de paquete según modo de sincronización seleccionado.
            # Con strict_sync=True (SYNC=2D D4), el payload útil son 26 bytes.
            # Con el truco AA 2D, el primer byte de payload es 0xD4 y la longitud es 27.
            self._base_pkt_len = pkt_len if pkt_len else 27
            # Determinar longitud según base y modo de sync.
            # Solo ajustar -1 en el caso clásico de 27→26; para 6‑in‑1 (34) no ajustar.
            plen = self._base_pkt_len
            self.radio.configure_bresser(plen)

            # Let AGC settle a bit
            sleep_ms(5)
            return True
        except Exception as e:
            if self.debug:
                print("WeatherSensor.begin error:", e)
            self.radio = None
            return False

    def receive(self, timeout_ms: int = 200) -> Optional[bytes]:
        """
        Block for up to timeout_ms and return a full packet (payload+status).

        Returns None if no packet is received.
        """
        if not self.radio:
            return None
        try:
            pkt = self.radio.read_packet(timeout_ms=timeout_ms)
            if self.debug and pkt:
                tohex = hexlify(pkt)
                #print("RX: ", tohex)
                print("RX(",len(tohex), '): ', tohex)
            return pkt
        except Exception as e:
            if self.debug:
                print("WeatherSensor.receive error:", e)
            # Try to recover by re-entering RX
            try:
                self.radio.enter_rx()
            except Exception:
                pass
            return None

    def reconfigure_sync(self, strict_sync: bool) -> bool:
        """Reconfigura dinámicamente el modo de sincronización (2D D4 vs AA 2D)
        y la longitud de paquete acorde. Devuelve True si se aplicó correctamente."""
        if not self.radio:
            return False
        try:
            plen = self._base_pkt_len
            self.radio.configure_bresser(plen)
            sleep_ms(2)
            try:
                self.radio.enter_rx()
            except Exception:
                pass

            return True
        except Exception as e:
            if self.debug:
                print('Error reconfigure_sync:', e)
            return False

    def reconfigure_bw(self, profile: str) -> bool:
        """Cambia el perfil de ancho de banda RX del CC1101 ('270k'|'250k')."""
        if not self.radio:
            return False
        try:
            ok = self.radio.set_bw_profile(profile)

            if ok:
                self._bw_profile = profile
                if self.debug:
                    print('BW reconfigurado ->', profile)
            return ok
        except Exception as e:
            if self.debug:
                print('Error reconfigure_bw:', e)
            return False

    # ---- Helpers ported from old C project for 6-in-1 decoding ----
    @staticmethod
    def _lfsr_digest16(data: bytes, length: int, gen: int = 0x8810, init: int = 0x5412) -> int:
        """
        LFSR-16 digest — exact port of WeatherSensor::lfsr_digest16 from the C project.

        The C algorithm shifts the KEY right and accumulates XOR in sum:
            sum = 0
            for each byte (MSB-first bit order):
                if bit set: sum ^= key
                if key&1:   key = (key >> 1) ^ gen
                else:       key >>= 1
            return sum

        IMPORTANT: this is NOT a left-shifting feedback register.
        The previous Python version (left-shift, fb=reg[15]^data_bit) produced
        incorrect digests for all Bresser packets.
        """
        key = init
        sum_val = 0
        for k in range(length):
            cur = data[k]
            for i in range(7, -1, -1):  # MSB first, same as C  (i = 7 downto 0)
                if (cur >> i) & 1:
                    sum_val ^= key
                if key & 1:
                    key = (key >> 1) ^ gen
                else:
                    key >>= 1
        return sum_val & 0xFFFF

    @staticmethod
    def _add_bytes_with_carry (data: bytes) -> int:
        """
        Calcula una suma simple de 16 bits de todos los bytes.
        """
        s = 0
        for x in data:
            s = (s + x) & 0xFFFF  # Realiza una suma simple acumulada a 16 bits
        return s

    @staticmethod
    def _bcd3(hn: int, ln: int, lo: int) -> int:
        """Convert three nibbles (H,L from one byte and high nibble of next) to decimal (like 100*a + 10*b + c)."""
        return (hn << 4) // 16 * 100 + (hn & 0x0F) * 0 + 0  # unused, kept for compatibility

    def decode(self, packet: bytes) -> Dict[str, Any]:
        """
        Decode a Bresser 6-in-1 or 5-in-1 payload like the old C project.

        Strategy for robust alignment:
        1) Try the two common layouts used so far:
           - 27 bytes with packet[0] == 0xD4 (message = bytes[1:27])
           - First 26 bytes as message.
        2) If both fail, scan all 26-byte sliding windows in the received bytes
           and try both decoders (6-in-1 then 5-in-1). Return the first success.
        This addresses off-by-one misalignment that can occur with different
        sync/preamble configurations or modules.
        """
        base_res: Dict[str, Any] = {
            "ok": False,
            "payload_hex": None,
            "sensor_id": None,
            "type": None,
            "chan": None,
            "battery_ok": None,
            # groups
            "temp_ok": False,
            "temp_c": None,
            "humidity_ok": False,
            "humidity": None,
            "wind_ok": False,
            "wind_gust_ms": None,
            "wind_avg_ms": None,
            "wind_dir_deg": None,
            "rain_ok": False,
            "rain_mm": None,
        }
        if not packet or len(packet) < 2:
            return base_res

        base_res["payload_hex"] = hexlify(packet).decode()

        # If driver is in variable-length mode, the first byte is the payload length (L),
        # optionally followed by L payload bytes and (if enabled) 2 status bytes.
        # Make the decoder resilient: if the packet matches that shape, strip the
        # length byte and (optionally) the trailing 2 status bytes.
        buf = packet
        try:
            L = packet[0]
            if 1 <= L <= 60:
                # Cases: [L | payload(L)]  or  [L | payload(L) | status(2)]
                if len(packet) == L + 1:
                    buf = packet[1:1+L]
                elif len(packet) == L + 3:
                    buf = packet[1:1+L]
        except Exception:
            buf = packet

        # From here on, "buf" should contain the pure payload bytes.
        packet = buf
        if len(packet) < 18:
            return base_res

        def _decode_6in1(msg: bytes) -> Optional[Dict[str, Any]]:
            try:
                chkdgst = (msg[0] << 8) | msg[1]
                digest = WeatherSensor._lfsr_digest16(msg[2:17], 15)
                if chkdgst != digest:
                    return None
                s = WeatherSensor._add_bytes_with_carry(msg[2:18])  # bytes 2..17 inclusive (16 bytes)
                if (s & 0xFF) != 0xFF:
                    return None
                out = dict(base_res)  # copy schema
                sensor_id = (msg[2] << 24) | (msg[3] << 16) | (msg[4] << 8) | msg[5]
                s_type = (msg[6] >> 4) & 0x0F
                chan = (msg[6] & 0x07)
                out["sensor_id"] = sensor_id
                out["type"] = s_type
                out["chan"] = chan
                # Temp/Humidity (per rtl_433 bresser_6in1.c):
                # - Temperature BCD in msg[15] (hundreds/tens) and upper nibble of msg[16] (ones)
                #   Value is in 0.1 C units; values > 600 represent negative temperatures as (raw-1000)
                # - Humidity BCD in msg[17] (two nibbles 0..9)
                temp_ok = ((msg[15] & 0xF0) <= 0x90) and ((msg[15] & 0x0F) <= 0x09) and ((msg[16] & 0xF0) <= 0x90)
                if temp_ok:
                    temp_raw = (msg[15] >> 4) * 100 + (msg[15] & 0x0F) * 10 + (msg[16] >> 4)
                    temp_c = temp_raw * 0.1
                    if temp_raw > 600:
                        temp_c = (temp_raw - 1000) * 0.1
                    out["temp_ok"] = True
                    out["temp_c"] = temp_c
                # Battery flag is encoded in msg[13] bit1 (per rtl_433); 1=OK
                out["battery_ok"] = ((msg[13] >> 1) & 1)
                hum_ok = ((msg[17] & 0xF0) <= 0x90) and ((msg[17] & 0x0F) <= 0x09)
                if hum_ok:
                    out["humidity_ok"] = True
                    out["humidity"] = (msg[17] >> 4) * 10 + (msg[17] & 0x0F)
                # Wind (bytes 7..11 after inversion on 7,8,9)
                m7 = msg[7] ^ 0xFF
                m8 = msg[8] ^ 0xFF
                m9 = msg[9] ^ 0xFF
                wind_ok = (m7 <= 0x99) and (m8 <= 0x99) and (m9 <= 0x99)
                if wind_ok:
                    gust_raw = (m7 >> 4) * 100 + (m7 & 0x0F) * 10 + (m8 >> 4)
                    wavg_raw = (m9 >> 4) * 100 + (m9 & 0x0F) * 10 + (m8 & 0x0F)
                    wind_dir_raw = ((msg[10] & 0xF0) >> 4) * 100 + (msg[10] & 0x0F) * 10 + ((msg[11] & 0xF0) >> 4)
                    out["wind_ok"] = True
                    out["wind_gust_ms"] = round(gust_raw * 0.1, 2)
                    out["wind_avg_ms"] = round(wavg_raw * 0.1, 2)
                    out["wind_dir_deg"] = round(float(wind_dir_raw), 2)
                # Rain counter (invert 12..14)
                r12 = msg[12] ^ 0xFF
                r13 = msg[13] ^ 0xFF
                r14 = msg[14] ^ 0xFF
                rain_ok = (r12 <= 0x65) and (r13 <= 0x99) and (r14 <= 0x99)
                if rain_ok:
                    rain_raw = (r12 >> 4) * 100000 + (r12 & 0x0F) * 10000 + (r13 >> 4) * 1000 + (r13 & 0x0F) * 100 + (r14 >> 4) * 10 + (r14 & 0x0F)
                    out["rain_ok"] = True
                    out["rain_mm"] = rain_raw * 0.1
                out["ok"] = any([out["temp_ok"], out["humidity_ok"], out["wind_ok"], out["rain_ok"]])
                return out if out["ok"] else None
            except Exception:
                return None

        def _decode_5in1(msg: bytes) -> Optional[Dict[str, Any]]:
            try:
                # Parity: first 13 bytes must be inverse of last 13 bytes
                for col in range(13):
                    if ((msg[col] ^ msg[col + 13]) & 0xFF) != 0xFF:
                        if _DECODE_DEBUG:
                            print('5in1 parity fail at col', col)
                        return None
                # Checksum: number of set bits in bytes 14..25 must equal msg[13]
                bits_set = 0
                for p in range(14, 26):
                    cur = msg[p]
                    while cur:
                        bits_set += (cur & 1)
                        cur >>= 1
                if bits_set != msg[13]:
                    if _DECODE_DEBUG:
                        print('5in1 checksum fail bits=', bits_set, ' expected=', msg[13])
                    return None
                out = dict(base_res)
                sensor_id = msg[14]
                type_full = msg[15] & 0x7F
                s_type = type_full & 0x0F
                out["sensor_id"] = sensor_id
                out["type"] = s_type
                out["chan"] = 0
                # Startup flag (per reference: MSb is 0 after power-on then 1 after ~1h, but ref snippet uses inverted)
                out["startup"] = True if ((msg[15] & 0x80) == 0) else False
                # Temperature (BCD) with sign nibble in msg[25] low nibble
                temp_raw = (msg[20] & 0x0F) + ((msg[20] >> 4) & 0x0F) * 10 + (msg[21] & 0x0F) * 100
                if (msg[25] & 0x0F) != 0:
                    temp_raw = -temp_raw
                out["temp_ok"] = (msg[20] & 0x0F) <= 9 and ((msg[20] >> 4) & 0x0F) <= 9 and (msg[21] & 0x0F) <= 9
                if out["temp_ok"]:
                    out["temp_c"] = temp_raw * 0.1
                # Humidity (BCD)
                hum_ok = (msg[22] & 0x0F) <= 9 and ((msg[22] >> 4) & 0x0F) <= 9
                out["humidity_ok"] = hum_ok
                if hum_ok:
                    out["humidity"] = (msg[22] & 0x0F) + ((msg[22] >> 4) & 0x0F) * 10
                # Wind — BUG FIX: nibbles were swapped vs C project reference.
                # C: wind_direction = ((msg[17] & 0xf0) >> 4) * 225 * 0.1 = HIGH nibble * 22.5
                # C: gust_raw = ((msg[17] & 0x0f) << 8) + msg[16]          = LOW nibble of [17]
                wind_dir_raw = ((msg[17] >> 4) & 0x0F) * 22.5
                gust_raw = ((msg[17] & 0x0F) << 8) | msg[16]
                wind_raw = (msg[18] & 0x0F) + ((msg[18] >> 4) & 0x0F) * 10 + (
                            msg[19] & 0x0F) * 100
                out["wind_ok"] = True
                out["wind_dir_deg"] = round(float(wind_dir_raw), 2)
                out["wind_gust_ms"] = round(gust_raw * 0.1, 2)
                out["wind_avg_ms"] = round(wind_raw * 0.1, 2)
                # Rain counter (BCD)
                rain_raw = (msg[23] & 0x0F) + ((msg[23] >> 4) & 0x0F) * 10 + (msg[24] & 0x0F) * 100 + ((msg[24] >> 4) & 0x0F) * 1000
                rain_mm = rain_raw * 0.1
                # Professional Rain Gauge detection (types 0x39..0x3B)
                if (type_full >= 0x39) and (type_full <= 0x3B):
                    rain_mm *= 2.5
                    # Map to WEATHER0 to simplify (as in reference); 0 is weather station in old project
                    out["type"] = 0
                    # No humidity/wind for rain gauge
                    out["humidity_ok"] = False
                    out["wind_ok"] = False
                out["rain_ok"] = True
                out["rain_mm"] = rain_mm
                # Battery (0=OK, 8=Low encoded in MSb)
                out["battery_ok"] = False if (msg[25] & 0x80) else True
                # Mark complete like reference
                out["ok"] = True
                out["complete"] = True
                return out
            except Exception:
                return None

        def _try_decoders(msg: bytes):
            order = [_decode_6in1, _decode_5in1]

            for fn in order:
                out = fn(msg)
                if out:
                    return out
            return None

        def _apply_filters(out: Dict[str, Any]) -> Dict[str, Any]:
            sid = out.get('sensor_id')
            filtered = False
            if sid is not None:
                if _SENSOR_EXC and sid in _SENSOR_EXC:
                    filtered = True
                if _SENSOR_INC and sid not in _SENSOR_INC:
                    filtered = True
            if filtered:
                if _DECODE_DEBUG:
                    print('Decodificado filtrado por ID:', sid)
                out = dict(out)
                out['filtered_out'] = True
                out['ok'] = False
            return out

        # 0) Fast path for 6-in-1.
        # When sync=AA2D, D4 is received as byte 0 and the 18-byte payload starts at [1].
        # When sync=2DD4 (strict), D4 is consumed by the sync word and payload starts at [0].
        if len(packet) >= 19 and packet[0] == 0xD4:
            out18 = _decode_6in1(packet[1:19])
            if out18:
                return _apply_filters(out18)
        if len(packet) >= 18:
            out18 = _decode_6in1(packet[:18])
            if out18:
                return _apply_filters(out18)

        # 1) Try common 26/27‑byte layouts first, honoring sync policy (mainly for 5‑in‑1 or legacy)
        candidates = []

        # Be permissive: try with and without D4 alignment
        if len(packet) >= 27 and packet[0] == 0xD4:
            candidates.append(packet[1:27])
        if len(packet) >= 26:
            candidates.append(packet[:26])

        for msg in candidates:
            out = _try_decoders(msg)
            if out:
                return _apply_filters(out)

        # 2) Sliding window fallback across the received bytes (optional)
        best: Optional[Dict[str, Any]] = None
        if _ALLOW_SLIDING_DECODE:
            n = len(packet)
            # 2.a) Try 6-in-1 18-byte windows (modern frames as seen by rtl_433 often embed 18B blocks)
            for offset in range(0, max(0, n - 18) + 1):
                msg18 = packet[offset:offset + 18]
                out = _decode_6in1(msg18)
                if out:
                    if self.debug:
                        out["align_offset"] = offset
                        out["align_len"] = 18
                    best = _apply_filters(out)
                    break
            # 2.b) If still not found, try legacy 26-byte windows for both 6-in-1 (old path) and 5-in-1
            if best is None:
                for offset in range(0, max(0, n - 26) + 1):
                    msg26 = packet[offset:offset + 26]
                    out = _try_decoders(msg26)
                    if out:
                        if self.debug:
                            out["align_offset"] = offset
                            out["align_len"] = 26
                        best = _apply_filters(out)
                        break
        res = best if best else base_res
        if _DECODE_DEBUG and not res.get('ok'):
            try:
                print('DECODE_DEBUG: fallo de decodificación. len=', len(packet), ' hex=', base_res.get('payload_hex'))
            except Exception:
                pass
        return res

    def probe_ids_from_packet(self, packet: bytes):
        """
        Try to extract candidate sensor IDs from a raw received packet without
        requiring a full successful decode. This is intended for FIND_STATION_IDS
        mode to discover which IDs are nearby.

        Strategy:
        - Scan all 26-byte windows inside the packet.
        - For 6-in-1, require valid digest and checksum, then read ID from bytes 2..5.
        - For 5-in-1, require 13/13 parity (XOR == 0xFF). If FIND_ID_STRICT=True,
          also require bitcount checksum to match; otherwise, accept parity-only
          matches as candidate IDs. The ID is byte[14].
        Returns a list of unique integer IDs.
        """
        ids = []
        if not packet or len(packet) < 18:
            return ids
        n = len(packet)
        def add_id(x):
            if x is None:
                return
            try:
                if x not in ids:
                    ids.append(x)
            except Exception:
                pass
        # First, scan 18-byte windows for 6-in-1
        for offset in range(0, max(0, n - 18) + 1):
            msg18 = packet[offset:offset + 18]
            try:
                chkdgst = (msg18[0] << 8) | msg18[1]
                digest = WeatherSensor._lfsr_digest16(msg18[2:17], 15)
                if chkdgst == digest:
                    s = WeatherSensor._add_bytes_with_carry(msg18[2:18])
                    if (s & 0xFF) == 0xFF:
                        sid6 = (msg18[2] << 24) | (msg18[3] << 16) | (msg18[4] << 8) | msg18[5]
                        add_id(sid6)
                        # Continue scanning for other IDs
            except Exception:
                pass
        # Then, scan 26-byte windows for 5-in-1 parity pattern
        for offset in range(0, max(0, n - 26) + 1):
            msg26 = packet[offset:offset + 26]
            try:
                parity_ok = True
                for col in range(13):
                    if ((msg26[col] ^ msg26[col + 13]) & 0xFF) != 0xFF:
                        parity_ok = False
                        break
                if parity_ok:
                    if _FIND_ID_STRICT:
                        bits_set = 0
                        for p in range(14, 26):
                            cur = msg26[p]
                            while cur:
                                bits_set += (cur & 1)
                                cur >>= 1
                        if bits_set != msg26[13]:
                            continue
                    sid5 = msg26[14]
                    add_id(sid5)
            except Exception:
                pass
        return ids