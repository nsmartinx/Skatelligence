import asyncio
from bleak import BleakClient, BleakScanner
import os

# UUID of the BLE characteristic to read
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

# Directory to save the received data
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'data/live/raw_data')

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# State to track current file number and packet count
current_file_number = 0
packet_count = 0
PACKETS_PER_FILE = 100  # Number of packets per file

async def handle_data(sender, data):
    """
    Callback to handle incoming data from the ESP32.
    Saves the data to a file in the UPLOAD_FOLDER.
    """
    global current_file_number, packet_count
    filename = f"{current_file_number}.bin"
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    with open(filepath, "ab") as f:  # Append to the file
        f.write(data)

    packet_count += 1
    print(f"Saved {len(data)} bytes to {filepath} (Packet {packet_count}/{PACKETS_PER_FILE})")

    # If enough packets are collected, finalize the file and increment the file number
    if packet_count >= PACKETS_PER_FILE:
        print(f"Finished writing file: {filename}")
        process_files()
        current_file_number += 1
        packet_count = 0

def process_files():
    """
    Placeholder for the file processing logic.
    Replace this with the actual logic from `data_processing`.
    """
    print("Processing files... (placeholder)")

async def connect_and_listen():
    """
    Continuously scans for the ESP32 BLE device, connects to it, and subscribes to notifications.
    Restarts the scanning process if the connection is lost.
    """
    while True:
        print("Scanning for BLE devices...")
        devices = await BleakScanner.discover()

        # Look for the ESP32 by name (adjust the name as necessary)
        target_device = None
        for device in devices:
            if "ESP32-S3-BLE" in device.name:  # Adjust this name to match your ESP32
                target_device = device
                break

        if not target_device:
            print("ESP32-S3 device not found. Retrying in 5 seconds...")
            await asyncio.sleep(5)
            continue

        print(f"Found ESP32-S3: {target_device.name} ({target_device.address})")
        print("Connecting...")

        try:
            async with BleakClient(target_device.address) as client:
                print(f"Connected to {target_device.name}")

                # Subscribe to notifications
                await client.start_notify(CHARACTERISTIC_UUID, handle_data)
                print("Subscribed to notifications. Listening for data...")

                while True:
                    await asyncio.sleep(1)  # Keep the connection alive
        except Exception as e:
            print(f"Connection error: {e}")
            print("Reconnecting...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(connect_and_listen())

