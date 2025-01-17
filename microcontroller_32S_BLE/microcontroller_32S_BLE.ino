#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include "Wire.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// BLE Service and Characteristic UUIDs
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// I2C and MPU setup
const int TCA_ADDR = 0x70; // I2C mux address
const int POLL_FREQUENCY_HZ = 100; // Frequency of IMU polling
const int POLL_INTERVAL_MS = 1000 / POLL_FREQUENCY_HZ;

// Callback to handle BLE connection and disconnection
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println("Client connected!");
  }
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("Client disconnected!");
    BLEDevice::getAdvertising()->start();
    Serial.println("Advertising restarted...");
  }
};

void tcaSelect(uint8_t i);
void setupMPU6050();
void readMPU6050(int16_t* Ax, int16_t* Ay, int16_t* Az, int16_t* Gx, int16_t* Gy, int16_t* Gz);
void readAndSendData(void * parameter);

void setup() {
  Serial.begin(115200);
  Serial.println("Starting BLE with IMU data transfer...");

  // BLE initialization
  BLEDevice::init("ESP32-S3-BLE-IMU");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());
  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pService->start();
  BLEDevice::getAdvertising()->start();
  Serial.println("BLE service started. Advertising...");

  // Initialize I2C
  Wire.begin(8, 9);
  Wire.setClock(400000);

  // Initialize accelerometers
  for (int i = 0; i < 5; i++) {
    tcaSelect(i);
    setupMPU6050();
  }

  // Create FreeRTOS task for reading and sending IMU data
  xTaskCreatePinnedToCore(readAndSendData, "Read and Send IMU Data", 10000, NULL, 1, NULL, 0);
}

void readAndSendData(void * parameter) {
  TickType_t xLastWakeTime = xTaskGetTickCount();
  const TickType_t xTimeIncrement = pdMS_TO_TICKS(POLL_INTERVAL_MS);

  while (1) {
    vTaskDelayUntil(&xLastWakeTime, xTimeIncrement);
    
    if (deviceConnected) {
      uint8_t payload[60]; // Fixed-size payload for BLE notifications
      int offset = 0;

      for (int i = 0; i < 5; i++) {
        int16_t Ax, Ay, Az, Gx, Gy, Gz;
        tcaSelect(i);
        readMPU6050(&Ax, &Ay, &Az, &Gx, &Gy, &Gz);

        // Pack data into payload
        memcpy(payload + offset, &Ax, sizeof(Ax));
        offset += sizeof(Ax);
        memcpy(payload + offset, &Ay, sizeof(Ay));
        offset += sizeof(Ay);
        memcpy(payload + offset, &Az, sizeof(Az));
        offset += sizeof(Az);
        memcpy(payload + offset, &Gx, sizeof(Gx));
        offset += sizeof(Gx);
        memcpy(payload + offset, &Gy, sizeof(Gy));
        offset += sizeof(Gy);
        memcpy(payload + offset, &Gz, sizeof(Gz));
        offset += sizeof(Gz);
      }

      // Send payload via BLE notification
      pCharacteristic->setValue(payload, sizeof(payload));
      pCharacteristic->notify();
      Serial.println("IMU data sent via BLE notification.");
    } else {
      Serial.println("Waiting for BLE connection...");
      vTaskDelay(pdMS_TO_TICKS(5000)); // Wait before retrying
    }
  }
}

void tcaSelect(uint8_t i) {
  if (i > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << i);
  Wire.endTransmission();
}

void setupMPU6050() {
  Wire.beginTransmission(0x68);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission();

  Wire.beginTransmission(0x68);
  Wire.write(0x1C);
  Wire.write(0x18);
  Wire.endTransmission();

  Wire.beginTransmission(0x68);
  Wire.write(0x1B);
  Wire.write(0x18);
  Wire.endTransmission();
}

void readMPU6050(int16_t* Ax, int16_t* Ay, int16_t* Az, int16_t* Gx, int16_t* Gy, int16_t* Gz) {
  Wire.beginTransmission(0x68);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(0x68, 14, true);

  *Ax = Wire.read() << 8 | Wire.read();
  *Ay = Wire.read() << 8 | Wire.read();
  *Az = Wire.read() << 8 | Wire.read();
  Wire.read(); Wire.read(); // Skip temperature readings
  *Gx = Wire.read() << 8 | Wire.read();
  *Gy = Wire.read() << 8 | Wire.read();
  *Gz = Wire.read() << 8 | Wire.read();
}

void loop() {
  // Empty - All tasks run in FreeRTOS
}
