#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;
unsigned long lastMicros = 0;

// Fixed 60-byte payload
uint8_t payload[60] = {0};

// Callback to handle client connection and disconnection
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println("Client connected!");
  }

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("Client disconnected!");
    // Start advertising again
    BLEDevice::getAdvertising()->start();
    Serial.println("Advertising restarted...");
  }
};

void setup() {
  // Start Serial Monitor for debugging
  Serial.begin(115200);
  Serial.println("Starting BLE...");

  // Initialize BLE and set the device name
  BLEDevice::init("ESP32-S3-BLE");

  // Create a BLE server and set callbacks
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create a BLE service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create a BLE characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  // Set an initial value for the characteristic
  memset(payload, 0, sizeof(payload)); // Initialize payload with zeros
  pCharacteristic->setValue(payload, sizeof(payload));

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->start();
  Serial.println("BLE service started. Advertising...");
}

void loop() {
  // Only send data if a device is connected
  if (deviceConnected) {
    unsigned long currentMicros = micros();
    if (currentMicros - lastMicros >= 10000) { // 10 ms interval for 100 Hz
      lastMicros = currentMicros;

      // Update payload (example: fill with incrementing counter values)
      static uint8_t counter = 0;
      for (int i = 0; i < sizeof(payload); i++) {
        payload[i] = counter++;
      }

      // Send the payload as a notification
      pCharacteristic->setValue(payload, sizeof(payload));
      pCharacteristic->notify();
      Serial.println("Sent 60-byte payload via BLE");
    }
  } else {
    // If no device is connected, print a debug message every 5 seconds
    static unsigned long lastDebugMillis = 0;
    if (millis() - lastDebugMillis > 5000) {
      lastDebugMillis = millis();
      Serial.println("Waiting for a client to connect...");
    }
  }
}
