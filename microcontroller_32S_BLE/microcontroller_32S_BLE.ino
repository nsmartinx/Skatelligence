#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>

#include <FS.h>
#include <SPIFFS.h>
#include <Wire.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

// FILE & SENSOR SETTINGS
const int TCA_ADDR = 0x70;           
const int POLL_FREQUENCY_HZ = 100;   
const int POLL_INTERVAL_MS = 1000 / POLL_FREQUENCY_HZ;
const int POLLS_PER_FILE = 100;     

int lastCompletedFile = -1;          
int lastUploadedFile  = -1;          

// BLE CHUNK SIZE
#define BLE_CHUNK_SIZE 200

// PROTOTYPES
void tcaSelect(uint8_t i);
void setupMPU6050();
void readMPU6050(int16_t* Ax, int16_t* Ay, int16_t* Az, int16_t* Gx, int16_t* Gy, int16_t* Gz);
void readDataTask(void * parameter);
void uploadDataTask(void * parameter);

// BLE SERVER CALLBACKS
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println("BLE Client connected!");
  }
  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println("BLE Client disconnected!");
    // Restart advertising so the client can reconnect
    BLEDevice::getAdvertising()->start();
    Serial.println("Advertising restarted...");
  }
};

void setup() {
  Serial.begin(115200);

  // Initialize SPIFFS
  if (!SPIFFS.begin(true)) {
    Serial.println("SPIFFS Mount Failed");
    return;
  } else {
    Serial.println("SPIFFS Mounted successfully");
  }

  // Initialize BLE
  BLEDevice::init("ESP32-BLE-FileUpload");
  BLEDevice::setMTU(247);
  
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);

  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->start();
  Serial.println("BLE service started. Advertising...");

  // Setup I2C / IMUs
  Wire.begin(8, 9);        
  Wire.setClock(400000);   

  // Initialize all 5 accelerometers
  for (int i = 0; i < 5; i++) {
    tcaSelect(i);
    setupMPU6050();
  }

  // Create tasks
  xTaskCreatePinnedToCore(
    readDataTask,
    "ReadDataTask",
    10000,
    NULL,
    1,
    NULL,
    0
  );

  xTaskCreatePinnedToCore(
    uploadDataTask,
    "UploadDataTask",
    10000,
    NULL,
    1,
    NULL,
    1
  );
}

void loop() {
  // Empty - all work is done in FreeRTOS tasks
}

// TASK 1: READ DATA AND WRITE TO FILE
void readDataTask(void * parameter) {
  TickType_t xLastWakeTime = xTaskGetTickCount();
  const TickType_t xTimeIncrement = pdMS_TO_TICKS(POLL_INTERVAL_MS);

  File file;
  int pollCount = 0;
  int fileNumber = 0;

  while (true) {
    vTaskDelayUntil(&xLastWakeTime, xTimeIncrement);

    // If file isn't open, open a new one
    if (!file) {
      String fileName = "/" + String(fileNumber) + ".bin";
      file = SPIFFS.open(fileName, FILE_WRITE);
      if (!file) {
        Serial.println("Failed to open file for writing");
      } else {
        Serial.println("Opened file: " + fileName);
      }
    }

    // Read from each of the 5 sensors
    for (int i = 0; i < 5; i++) {
      int16_t Ax, Ay, Az, Gx, Gy, Gz;
      tcaSelect(i);
      readMPU6050(&Ax, &Ay, &Az, &Gx, &Gy, &Gz);

      // Write raw binary data
      file.write((uint8_t*)&Ax, sizeof(Ax));
      file.write((uint8_t*)&Ay, sizeof(Ay));
      file.write((uint8_t*)&Az, sizeof(Az));
      file.write((uint8_t*)&Gx, sizeof(Gx));
      file.write((uint8_t*)&Gy, sizeof(Gy));
      file.write((uint8_t*)&Gz, sizeof(Gz));
    }

    pollCount++;

    // If we've reached POLLS_PER_FILE, close it and signal "done"
    if (pollCount >= POLLS_PER_FILE) {
      file.close();
      Serial.println("Finished writing file: " + String(fileNumber) + ".bin");
      lastCompletedFile = fileNumber;
      fileNumber++;
      pollCount = 0;
    }
  }
}

// TASK 2: UPLOAD FILES OVER BLE
void uploadDataTask(void * parameter) {
  while (true) {
    // If we have a new file completed that hasn't been uploaded
    if (deviceConnected && (lastUploadedFile < lastCompletedFile)) {
      int nextFileToUpload = lastUploadedFile + 1;
      String fileName = "/" + String(nextFileToUpload) + ".bin";
      File fileToUpload = SPIFFS.open(fileName, FILE_READ);

      if (!fileToUpload) {
        Serial.println("Failed to open file for uploading: " + fileName);
      } else {
        Serial.println("Uploading file over BLE: " + fileName);
        
        // Read the file in BLE_CHUNK_SIZE chunks
        while (fileToUpload.available()) {
          uint8_t buffer[BLE_CHUNK_SIZE];
          int bytesRead = fileToUpload.read(buffer, BLE_CHUNK_SIZE);

          // If device is still connected, send the notification
          if (deviceConnected) {
            pCharacteristic->setValue(buffer, bytesRead);
            pCharacteristic->notify();

            // A small delay to avoid flooding the BLE stack
            vTaskDelay(pdMS_TO_TICKS(10));
          } else {
            Serial.println("BLE device disconnected mid-upload");
            break;
          }
        }

        fileToUpload.close();
        if (deviceConnected) {
          lastUploadedFile = nextFileToUpload;
          Serial.println("Upload complete for file: " + fileName);
        }
      }
    }
    vTaskDelay(pdMS_TO_TICKS(1));
  }
}

// TCA9548A SELECT
void tcaSelect(uint8_t i) {
  if (i > 7) return;
  Wire.beginTransmission(TCA_ADDR);
  Wire.write(1 << i);
  Wire.endTransmission();
}

// MPU6050 SETUP
void setupMPU6050() {
  Wire.beginTransmission(0x68);
  Wire.write(0x6B);
  Wire.write(0);
  Wire.endTransmission();

  // Accelerometer config (+16g)
  Wire.beginTransmission(0x68);
  Wire.write(0x1C);
  Wire.write(0x18);
  Wire.endTransmission();

  // Gyroscope config (+2000 deg/s)
  Wire.beginTransmission(0x68);
  Wire.write(0x1B);
  Wire.write(0x18);
  Wire.endTransmission();
}

// READ MPU6050
void readMPU6050(int16_t* Ax, int16_t* Ay, int16_t* Az, 
                 int16_t* Gx, int16_t* Gy, int16_t* Gz) {
  Wire.beginTransmission(0x68);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(0x68, 14, true);

  *Ax = Wire.read() << 8 | Wire.read();
  *Ay = Wire.read() << 8 | Wire.read();
  *Az = Wire.read() << 8 | Wire.read();

  // Skip temperature registers
  Wire.read(); 
  Wire.read();

  *Gx = Wire.read() << 8 | Wire.read();
  *Gy = Wire.read() << 8 | Wire.read();
  *Gz = Wire.read() << 8 | Wire.read();
}

// OPTIONAL: WIPE SPIFFS
void wipeSPIFFS() {
  Serial.println("Wiping SPIFFS...");
  File root = SPIFFS.open("/");
  if (!root || !root.isDirectory()) {
    Serial.println("Failed to open root directory or not a directory");
    return;
  }

  File file = root.openNextFile();
  while (file) {
    String filePath = String("/") + String(file.name());
    Serial.print("Deleting file: ");
    Serial.println(filePath);
    if (SPIFFS.remove(filePath)) {
      Serial.println("File deleted");
    } else {
      Serial.println("ERROR: Delete failed");
    }
    file = root.openNextFile();
  }
}
