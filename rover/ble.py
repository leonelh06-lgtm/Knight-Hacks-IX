"""Existing mBot firmware: fixed-speed W/A/D/X, 500 ms watchdog."""
import asyncio

CHARACTERISTIC='0000ffe3-0000-1000-8000-00805f9b34fb'

class MotorLink:
    def __init__(self, name, decision_source, *, client_factory=None, on_fault=None):
        self.name=name
        self.source=decision_source
        self.factory=client_factory
        self.on_fault=on_fault or (lambda reason:None)
        self.connected=False
        self.stopping=False

    def request_stop(self):
        self.stopping=True

    async def _client(self):
        if self.factory:return self.factory(self.name)
        # Lazy import: dry-run never discovers or connects a physical rover.
        from bleak import BleakClient, BleakScanner
        device=await BleakScanner.find_device_by_name(self.name,timeout=10)
        if device is None:raise RuntimeError(f'BLE device not found: {self.name}')
        return BleakClient(device,timeout=10)

    async def run(self, stop_event):
        client=None
        try:
            client=await self._client()
            await asyncio.wait_for(client.connect(),timeout=12)
            await asyncio.wait_for(client.write_gatt_char(CHARACTERISTIC,b'X',response=False),timeout=.2)
            self.connected=True
            while not stop_event.is_set():
                if not client.is_connected:raise ConnectionError('BLE disconnected')
                decision=self.source()
                command=b'X' if self.stopping or not decision.armed else decision.command
                if command not in (b'W',b'A',b'D',b'X'):raise ValueError('Invalid motor intent')
                await asyncio.wait_for(client.write_gatt_char(CHARACTERISTIC,command,response=False),timeout=.2)
                try:await asyncio.wait_for(stop_event.wait(),timeout=.1)
                except TimeoutError:pass
        except BaseException:
            self.on_fault('BLE link stopped; explicit re-arm required')
            raise
        finally:
            self.connected=False
            self.stopping=True
            if client is not None:
                try:await asyncio.wait_for(client.write_gatt_char(CHARACTERISTIC,b'X',response=False),timeout=.2)
                except (Exception,asyncio.CancelledError):pass
                try:await asyncio.wait_for(client.disconnect(),timeout=1)
                except (Exception,asyncio.CancelledError):pass
