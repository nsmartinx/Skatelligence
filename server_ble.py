import asyncio
from bleak import BleakClient, BleakScanner
from data_processing import process_files
import os

# UUID of the BLE characteristic to read
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# Directory to save the received data
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data/live/raw_data')

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# State to track current file number
current_file_number = 0

# Buffer to accumulate the file data
FILE_SIZE_BYTES = 6000
acc_buffer = bytearray()

async def handle_data(sender, data):
    """
    Callback to handle incoming data from the ESP32.
    We accumulate data in a global buffer until we reach FILE_SIZE_BYTES,
    then write to a single .bin file.
    
    Note: We are expecting ~200-byte packets (instead of the typical 20-byte
    default), but the exact size may vary depending on your BLE peripheral
    configuration.
    """
    global current_file_number, acc_buffer

    # Accumulate this chunk
    acc_buffer.extend(data)

    print(f"Received {len(data)} bytes. Total accumulated: {len(acc_buffer)} bytes.")

    # Check if we have a complete file in buffer
    if len(acc_buffer) >= FILE_SIZE_BYTES:
        # Slice out exactly FILE_SIZE_BYTES if there's extra
        file_data = acc_buffer[:FILE_SIZE_BYTES]
        # Keep any leftover (in case multiple files arrive back to back)
        acc_buffer = acc_buffer[FILE_SIZE_BYTES:]

        # Write the complete file
        filename = f"{current_file_number}.bin"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        with open(filepath, "wb") as f:
            f.write(file_data)
        
        print(f"Saved {FILE_SIZE_BYTES} bytes to {filepath}")
        print(f"Finished writing file: {filename}")

        # Increment file number
        current_file_number += 1

        process_files()

async def connect_and_listen():
    """
    Continuously scans for the ESP32 BLE device, connects to it,
    and subscribes to notifications. Restarts the scanning process
    if the connection is lost.
    """
    while True:
        print("Scanning for BLE devices...")
        devices = await BleakScanner.discover()

        # Look for the ESP32 by name (adjust as necessary)
        target_device = None
        for device in devices:
            if "ESP32-BLE-FileUpload" in device.name:
                target_device = device
                break

        if not target_device:
            print("ESP32 device not found. Retrying in 5 seconds...")
            await asyncio.sleep(5)
            continue

        print(f"Found ESP32: {target_device.name} ({target_device.address})")
        print("Connecting...")

        try:
            async with BleakClient(target_device.address) as client:
                print(f"Connected to {target_device.name}")

                # Subscribe to notifications
                await client.start_notify(CHARACTERISTIC_UUID, handle_data)
                print("Subscribed to notifications. Listening for data...")

                # Keep the connection alive
                while True:
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Connection error: {e}")
            print("Reconnecting...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(connect_and_listen())

