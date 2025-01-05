import asyncio
from bleak import BleakClient, BleakScanner

# Replace with the UUID of the characteristic you want to read
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

async def handle_data(sender, data):
    """
    Callback to handle incoming data from the ESP32.
    Prints the data to the console.
    """
    print(f"Data from {sender}: {data.decode('utf-8')}")

async def connect_to_esp32():
    """
    Scans for the ESP32 BLE device, connects to it, and subscribes to notifications.
    """
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover()

    # Look for the ESP32 by name (adjust the name as necessary)
    target_device = None
    for device in devices:
        if "ESP32-S3-BLE" in device.name:  # Adjust this name to match your ESP32
            target_device = device
            break

    if not target_device:
        print("ESP32-S3 device not found. Make sure it's advertising and try again.")
        return

    print(f"Found ESP32-S3: {target_device.name} ({target_device.address})")
    print("Connecting...")

    async with BleakClient(target_device.address) as client:
        print(f"Connected to {target_device.name}")

        # Fetch and iterate over services and characteristics
        await client.get_services()
        characteristic_found = False

        for service in client.services:
            for char in service.characteristics:
                if char.uuid == CHARACTERISTIC_UUID:
                    characteristic_found = True
                    break
            if characteristic_found:
                break

        if not characteristic_found:
            print(f"Characteristic {CHARACTERISTIC_UUID} not found!")
            return

        # Subscribe to notifications
        await client.start_notify(CHARACTERISTIC_UUID, handle_data)
        print("Subscribed to notifications. Listening for data...")

        try:
            while True:
                await asyncio.sleep(1)  # Keep the connection alive
        except KeyboardInterrupt:
            print("\nDisconnecting...")
            await client.stop_notify(CHARACTERISTIC_UUID)

if __name__ == "__main__":
    asyncio.run(connect_to_esp32())

