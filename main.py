import can
import time

class ECUDiagnostic:
    """Class to handle ECU diagnostics using CAN FD bus and Vector Hardware"""

    def __init__(self, tx_id, app_name='python-can', channel=0, bitrate=500000, data_bitrate=2000000):
        # ECU properties
        self.tx_id = tx_id

        # CAN hardware configuration
        self.app_name = app_name
        self.channel = channel
        self.bitrate = bitrate
        self.data_bitrate = data_bitrate

        # Bus instance (initially empty)
        self.bus = None

    def connect(self):
        """Connect to the CAN bus using Vector hardware"""
        print(f"Opening connection with Vector VN1610 (Channel {self.channel})...")
        self.bus = can.interface.Bus(
            bustype='vector', 
            channel=self.channel, 
            bitrate=self.bitrate, 
            data_bitrate=self.data_bitrate
        )
        print("Connection CAN established.")

    def disconnect(self):
        """Disconnect from the CAN bus"""
        if self.bus:
            self.bus.shutdown()
            print("Connection CAN closed.")

    def _send_and_wait_for_response(self, payload, service_tx, timeout=2.0):
        """Send a diagnostic request and wait for the response"""
        if not self.bus:
            raise RuntimeError("CAN bus is not connected, call connect() first.")
        
        tx_message = can.Message(
            arbitration_id=self.tx_id,
            data=payload,
            is_extended_id=False,
            is_fd=True
        )

        print(f"\n[TX] ID: {hex(self.tx_id)}| Payload: {[hex(b) for b in payload]}")
        self.bus.send(tx_message)
        start_time = time.time()
        expected_rx_service = service_tx + 0x40  # Expected response service ID

        while(time.time() - start_time) < timeout:
            response = self.bus.recv(timeout=0.1)
            if response is not None and len(response.data) >= 3:
                # Check positive response
                if response.data[1] == expected_rx_service:
                    print(f"[RX OK] ID: {hex(response.arbitration_id)}| Data: {[hex(b) for b in response.data]}")
                    return True, response.data
                # Check for negative response
                elif response.data[1] == 0x7F and response.data[2] == service_tx:
                    print(f"[RX NRC] Failure. NRC code: {hex(response.data[3])}")
                    return False, response.data
                
        print(f"[RX] No response received in {timeout} seconds.")
        return False, None
        
    def request_default_session(self):
        """Request the ECU to switch to Default Session (0x10 0x01)"""
        print("--- Resquesting Default Session ---")
        payload = [0x02, 0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]  # Length, Service ID, Session Type
        success, data = self._send_and_wait_for_response(payload, service_tx=0x10)
        if success and data[2] == 0x01:
            print("ECU in Default Session")
            return True
        return False
    
    def request_extended_session(self):
        """Request the ECU to switch to Extended Session (0x10 0x03)"""
        print("--- Requesting Extended Session ---")
        payload = [0x02, 0x10, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]  # Length, Service ID, Session Type
        success, data = self._send_and_wait_for_response(payload, service_tx=0x10)
        if success and data[2] == 0x03:
            print("ECU in Extended Session")
            return True
        return False
    
    def read_did(self, *did_bytes:int):
        """Read a Diagnostic Identifier (DID) from the ECU"""
        if not did_bytes:
            raise ValueError("DID cannot be empty.")
        
        did_len = len(did_bytes)
        # PCI length = 1 byte for service ID (0x22) + number of DID bytes
        pci_length = 1 + did_len

        # create a user-friendly string for the DID for logging
        did_str = ' '.join([f"{b:02X}" for b in did_bytes])
        print(f"---Reading data (DID {did_str})---")

        # Build the payload: [PCI Length, Service ID, DID bytes..., padding...]
        payload = [pci_length, 0x22] + list(did_bytes)
        # padd the rest of the payload with zeros
        payload.extend([0x00] * (8 - len(payload)))

        success, data = self._send_and_wait_for_response(payload, service_tx=0x22)

        if success:
            # Positive response format: [PCI Length, Service ID + 0x40, DID bytes..., data bytes...]
            response_pci_len = data[0]
            value_start_index = 1 + 1 + did_len  # PCI byte + Service ID byte + DID bytes
            ecu_value = data[value_start_index:response_pci_len + 1]
            print(f"-> Extracted Value: {[hex(b) for b in ecu_value]}")
            return ecu_value
        else:
            print("Failed to read DID.")
        return None
    
    def request_hard_reset(self):
        """Sends a hardware reset request to the ECU (0x11 0x01)"""
        print("--- Requesting Hard Reset ---")
        payload = [0x02, 0x11, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00]  # Length, Service ID, Reset Type
        success, data = self._send_and_wait_for_response(payload, service_tx=0x11)

        if success:
            print("-> Success: ECU accepted the reset. Awaiting recovery (3s)")
            time.sleep(3) # pause to allow microncontroller to restart
            return True
        return False
    

def main():
    # Instantiate the object paasing the transmission ID for DIAGNOSTIC_REQUEST_FD_IPC
    ecu_ipc = ECUDiagnostic(tx_id=0x98DA60F2, channel=0)

    try:
        # initialize the hardware
        ecu_ipc.connect()

        # execute our diagnostic sequence as method calls
        ecu_ipc.request_default_session()
        time.sleep(0.1)

        ecu_ipc.read_did(0xF1, 0x86)
        time.sleep(0.1)

        if ecu_ipc.request_extended_session():
            time.sleep(0.1)

            # read DID F1 A0
            ecu_ipc.read_did(0xF1, 0x86)
            time.sleep(0.1)

            # reset the ECU
            ecu_ipc.request_hard_reset()
        else:
            print("\n Sequence aborted: Failed to enter Extended Session.")

    except Exception as e:
        print("\n Error during execution")

    finally:
        # ensure the bus is closed
        ecu_ipc.disconnect()


if __name__ == "__main__":
    print("Starting Diagnostic session")
    main()