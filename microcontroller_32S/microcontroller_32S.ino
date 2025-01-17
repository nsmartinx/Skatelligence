#include <WiFi.h>
#include <HTTPClient.h>
#include "FS.h"
#include "SD.h"
#include "SPI.h"
#include "Wire.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// SPI pin numbers
#define CS   5

// Wifi information
const char* ssid     = "<Wifi Name>";
const char* password = "<Wifi Password>";
const char* serverName = "http://<IP Address>:5000/postdata";

const int TCA_ADDR = 0x70; // I2C mux adress
const int POLL_FREQUENCY_HZ = 100; // Frequency of IMU polling
const int POLL_INTERVAL_MS = 1000 / POLL_FREQUENCY_HZ;
const int POLLS_PER_FILE = 100; // Number of IMU measurements per file

int lastCompletedFile = -1; // Last file number that has been written and is ready to upload

void tcaSelect(uint8_t i);
void setupMPU6050();
void readMPU6050(int16_t* Ax, int16_t* Ay, int16_t* Az, int16_t* Gx, int16_t* Gy, int16_t* Gz);
void dataLogger(void * parameter);
void fileUploader(void * parameter);
void wipeSDCard();
void initializeWifi();
void readData(void * parameter);
void uploadData(void * parameter);

void setup() {
    Serial.begin(115200); // Serial communication baud rate
    Wire.begin(21, 22); // Pins for I2C communication to TCA (SDA, SCL)
    Wire.setClock(400000); // I2C Clock speed (400 kHz)

    // Initialize SD card
    while (!SD.begin(CS)) {
        Serial.println("Card Mount Failed");
        SPI.end();
        delay(100);
        SPI.begin();
        delay(100);
    }

    // Wipe the SD card
    wipeSDCard();

    // Initialize all accelerometers
    for (int i = 0; i < 5; i++) {
        tcaSelect(i);
        setupMPU6050();
    }

    // Start Wi-Fi connection
    initializeWifi();

    for (int i = 0; i < 5; i++) {
        int16_t Ax, Ay, Az, Gx, Gy, Gz;
        tcaSelect(i);
        readMPU6050(&Ax, &Ay, &Az, &Gx, &Gy, &Gz);
        Serial.print("Sensor: ");
        Serial.print(i);
        Serial.print(" ");
        Serial.print(Ax);
        Serial.print(Ay);
        Serial.print(Az);
        Serial.print(Gx);
        Serial.print(Gy);
        Serial.println(Gz);
    }
    

    // Create tasks
    xTaskCreatePinnedToCore(readData, "Read Data", 10000, NULL, 1, NULL, 0); // Core 0
    xTaskCreatePinnedToCore(uploadData, "Upload Data", 10000, NULL, 1, NULL, 1); // Core 1
}

void ScanWifi(){
    Serial.println("Scanning for WiFi networks...");
    int n = WiFi.scanNetworks();
    if (n == 0) {
        Serial.println("No networks found.");
    } else {
        Serial.print(n);
        Serial.println(" networks found:");
    for (int i = 0; i < n; ++i) {
      // Print SSID and RSSI for each network found
      Serial.print(i + 1);
      Serial.print(": ");
      Serial.print(WiFi.SSID(i));
      Serial.print(" (");
      Serial.print(WiFi.RSSI(i));
      Serial.println(" dBm)");
      delay(10);
    }
  }
}

void initializeWifi(){
    Serial.println("\nConnecting to WiFi...");
    ScanWifi();
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("");
    Serial.println("WiFi connected successfully");
    Serial.print("Assigned IP Address: ");
    Serial.println(WiFi.localIP());
}

void wipeSDCard() {
    File root = SD.open("/");
    if (!root) {
        Serial.println("Failed to open directory");
        return;
    }
    if (!root.isDirectory()) {
        Serial.println("ERROR: Not a directory");
        root.close();
        return;
    }

    File file = root.openNextFile();
    while (file) {
        String filePath = String("/") + String(file.name());
        if (file.isDirectory()) {
            Serial.print("ERROR: Directory found called: ");
            Serial.println(filePath);
        } else {
            Serial.print("Deleting file: ");
            Serial.println(filePath);
            if (SD.remove(filePath.c_str())) {
                Serial.println("File deleted");
            } else {
                Serial.println("ERROR: Delete failed");
            }
        }
        file.close();
        file = root.openNextFile();
    }
    root.close();
}


void readData(void * parameter) {
    TickType_t xLastWakeTime;
    const TickType_t xTimeIncrement = pdMS_TO_TICKS(POLL_INTERVAL_MS);
    
    File file;
    int pollCount = 0;
    int fileNumber = 0;
    
    // Initialize xLastWakeTime with the current time
    xLastWakeTime = xTaskGetTickCount();

    while (1) {
        // Wait until xTimeIncrement after xLastWakeTime
        vTaskDelayUntil(&xLastWakeTime, xTimeIncrement);

        if (!file){
            String fileName = "/" + String(fileNumber) + ".bin";
            file = SD.open(fileName, FILE_WRITE);
                if (!file) {
                    Serial.println("Failed to open file for writing");
                } else {
                    Serial.println("File opened successfully: " + fileName);
                }
        }
        
        for (int i = 0; i < 5; i++) {
            int16_t Ax, Ay, Az, Gx, Gy, Gz;
            tcaSelect(i);
            readMPU6050(&Ax, &Ay, &Az, &Gx, &Gy, &Gz);
            file.write((byte*)&Ax, sizeof(Ax));
            file.write((byte*)&Ay, sizeof(Ay));
            file.write((byte*)&Az, sizeof(Az));
            file.write((byte*)&Gx, sizeof(Gx));
            file.write((byte*)&Gy, sizeof(Gy));
            file.write((byte*)&Gz, sizeof(Gz));
        }

        pollCount++;

        // Check if this file is done
        if (pollCount >= POLLS_PER_FILE) {
            file.close();
            Serial.println("Finished writing to file: /" + String(fileNumber) + ".bin");
            lastCompletedFile = fileNumber; // Update the last completed file index
            fileNumber++;
            pollCount = 0;
        }
    }
}

void uploadData(void * parameter) {
    int lastUploadedFile = -1;
    while (1) {
        if (lastUploadedFile < lastCompletedFile) {
            String fileName = "/" + String(lastUploadedFile + 1) + ".bin";
            File fileToUpload = SD.open(fileName, FILE_READ);
            if (!fileToUpload) {
                Serial.println("Failed to open file for uploading");
            } else {
                Serial.println("Uploading file: " + fileName);
                if(WiFi.status() == WL_CONNECTED) {
                    HTTPClient http;
                    http.begin(serverName);
                    http.addHeader("Content-Type", "multipart/form-data; boundary=123456");

                    // Prepare the multipart/form-data body
                    String preData = "--123456\r\nContent-Disposition: form-data; name=\"file\"; filename=\"";
                    preData += String(fileName) + "\"\r\nContent-Type: application/octet-stream\r\n\r\n";
                    String postData = "\r\n--123456--\r\n";

                    // Read entire file into memory
                    String fileData;
                    while(fileToUpload.available()) {
                        fileData += (char)fileToUpload.read();
                    }

                    // Calculate content length
                    size_t totalSize = preData.length() + fileData.length() + postData.length();
                    http.addHeader("Content-Length", String(totalSize));

                    // Send the complete POST request
                    int httpResponseCode = http.POST(preData + fileData + postData);

                    if(httpResponseCode >= 200 && httpResponseCode <= 299) {
                        String response = http.getString();
                        Serial.print("Upload successful: HTTP Code ");
                        Serial.println(httpResponseCode);
                        Serial.println(response);
                        lastUploadedFile++; // Increment only on successful upload
                    } else {
                        Serial.print("Error on sending POST: HTTP Code ");
                        Serial.println(httpResponseCode);
                        if (httpResponseCode > 0) {
                            String response = http.getString();
                            Serial.println(response); // Print the error response
                        }
                    }
                    http.end();
                } else {
                    Serial.println("Error in WiFi connection");
                }
                fileToUpload.close();
            }
        }
        vTaskDelay(pdMS_TO_TICKS(10)); // Delay before trying again
    }
}

void tcaSelect(uint8_t i) {
    if (i > 7) return;
    Wire.beginTransmission(TCA_ADDR);
    Wire.write(1 << i);
    Wire.endTransmission();
}

void setupMPU6050() {
    Wire.beginTransmission(0x68); // MPU6050 address
    Wire.write(0x6B); // PWR_MGMT_1 register
    Wire.write(0);    // Set to zero (wakes up the MPU-6050)
    Wire.endTransmission();

    Wire.beginTransmission(0x68);
    Wire.write(0x1C); // Accelerometer Configuration register
    Wire.write(0x18); // +/- 16g range
    Wire.endTransmission();

    Wire.beginTransmission(0x68);
    Wire.write(0x1B); // Gyroscope Configuration register
    Wire.write(0x18); // +/- 2000 deg/s range
    Wire.endTransmission();
}

void readMPU6050(int16_t* Ax, int16_t* Ay, int16_t* Az, int16_t* Gx, int16_t* Gy, int16_t* Gz) {
    Wire.beginTransmission(0x68); // MPU6050 address
    Wire.write(0x3B);             // Starting register for Accel Readings
    Wire.endTransmission(false);
    Wire.requestFrom(0x68, 14, true); // Request 14 registers

    *Ax = Wire.read() << 8 | Wire.read();
    *Ay = Wire.read() << 8 | Wire.read();
    *Az = Wire.read() << 8 | Wire.read();
    Wire.read(); Wire.read(); // Skip temperature
    *Gx = Wire.read() << 8 | Wire.read();
    *Gy = Wire.read() << 8 | Wire.read();
    *Gz = Wire.read() << 8 | Wire.read();
}

void loop() {
    // Empty
}
