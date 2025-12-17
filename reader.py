"""
LLRP RFID Reader Client
Connects to an LLRP RFID reader and reports tag reads via callback
"""
import socket
import struct
import logging
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LLRP_DEFAULT_PORT = 5084


class LLRPReader:
    """LLRP RFID Reader Client"""
    
    def __init__(self, host, port=LLRP_DEFAULT_PORT, tag_callback=None):
        self.host = host
        self.port = port
        self.sock = None
        self.running = False
        self.tag_callback = tag_callback  # Callback function for tag reads
        self.read_thread = None
    
    def connect(self):
        """Establishes a TCP connection to the LLRP reader"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            logger.info(f"Connecting to {self.host}:{self.port}...")
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            logger.info("Connected successfully.")
        except socket.error as e:
            logger.error(f"Connection failed: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from the reader"""
        self.stop()
        if self.sock:
            self.sock.close()
            self.sock = None
            logger.info("Disconnected from reader.")
    
    def _recv_exact(self, n):
        """Helper to receive exactly n bytes"""
        data = b''
        while len(data) < n:
            packet = self.sock.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data
    
    def send_message(self, msg_type, payload=b'', msg_id=0):
        """Constructs and sends an LLRP message"""
        first_word = (1 << 10) | (msg_type & 0x03FF)
        length = 10 + len(payload)
        header = struct.pack('!HII', first_word, length, msg_id)
        self.sock.sendall(header + payload)
        logger.debug(f"Sent Message: Type={msg_type}, Length={length}, ID={msg_id}")
    
    def _parse_header(self, header_bytes):
        """Parses the LLRP message header"""
        if len(header_bytes) < 10:
            return None
        first_word, length, msg_id = struct.unpack('!HII', header_bytes)
        version = (first_word >> 10) & 0x07
        msg_type = first_word & 0x03FF
        return {
            'version': version,
            'type': msg_type,
            'length': length,
            'id': msg_id
        }
    
    def _parse_epc_from_payload(self, payload):
        """Extract EPC data from RO_ACCESS_REPORT payload"""
        epcs = []
        offset = 0
        
        while offset < len(payload):
            if offset + 4 > len(payload):
                break
            
            first_word, length = struct.unpack('!HH', payload[offset:offset+4])
            param_type = first_word & 0x03FF
            
            if param_type == 240:  # TagReportData
                content = payload[offset+4:offset+length]
                epc = self._extract_epc_from_tag_report(content)
                if epc:
                    epcs.append(epc)
            
            offset += length
        
        return epcs
    
    def _extract_epc_from_tag_report(self, data):
        """Extract EPC from TagReportData"""
        offset = 0
        while offset < len(data):
            if offset + 1 > len(data):
                break
            
            b0 = data[offset]
            
            if b0 & 0x80:  # TV Parameter
                tv_type = b0 & 0x7F
                offset += 1
                # Skip TV parameter values
                if tv_type == 1:  # AntennaID
                    offset += 1
                elif tv_type == 6:  # PeakRSSI
                    offset += 1
                elif tv_type in [2, 3, 4, 5]:  # Timestamps
                    offset += 8
                elif tv_type in [7, 8, 10, 11, 12, 14, 15, 16]:
                    offset += 2
                elif tv_type in [9, 13]:
                    offset += 4
                else:
                    break
            else:  # TLV Parameter
                if offset + 4 > len(data):
                    break
                first_word, length = struct.unpack('!HH', data[offset:offset+4])
                param_type = first_word & 0x03FF
                content = data[offset+4:offset+length]
                
                if param_type == 241:  # EPCData
                    if len(content) > 2:
                        epc_len_bits = struct.unpack('!H', content[0:2])[0]
                        epc_len_bytes = (epc_len_bits + 7) // 8
                        epc = content[2:2+epc_len_bytes]
                        return epc.hex()
                elif param_type == 13:  # EPC-96
                    return content.hex()
                
                offset += length
        
        return None
    
    def start_reading(self):
        """Start the reader in a background thread"""
        if self.running:
            logger.warning("Reader is already running")
            return
        
        self.running = True
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
        logger.info("Reader started")
    
    def stop(self):
        """Stop the reader"""
        self.running = False
        if self.read_thread:
            self.read_thread.join(timeout=2)
        logger.info("Reader stopped")
    
    def _read_loop(self):
        """Main reading loop (runs in background thread)"""
        try:
            while self.running:
                header_data = self._recv_exact(10)
                if not header_data:
                    logger.warning("Connection closed by server")
                    break
                
                header = self._parse_header(header_data)
                payload_len = header['length'] - 10
                payload = b''
                
                if payload_len > 0:
                    payload = self._recv_exact(payload_len)
                    if not payload:
                        logger.warning("Incomplete payload received")
                        break
                
                # Process RO_ACCESS_REPORT (Type 61)
                if header['type'] == 61:
                    epcs = self._parse_epc_from_payload(payload)
                    for epc in epcs:
                        if self.tag_callback:
                            self.tag_callback(epc)
                        else:
                            logger.info(f"Tag Read: {epc}")
        
        except Exception as e:
            logger.error(f"Error in read loop: {e}")
        finally:
            self.running = False


# Standalone test mode
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python reader.py <READER_IP>")
        sys.exit(1)
    
    def tag_read_callback(epc):
        print(f"TAG READ: {epc}")
    
    reader = LLRPReader(sys.argv[1], tag_callback=tag_read_callback)
    try:
        reader.connect()
        reader.start_reading()
        
        # Keep running until Ctrl+C
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.disconnect()
