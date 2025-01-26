#include <WiFi.h>
#include <HTTPClient.h>
#include "FS.h"
#include "SPIFFS.h"
#include "Wire.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// Wifi information
const char* ssid     = "<WIFI Name>";
const char* password = "<Password>";
const char* serverName = "http://<IP Address>:5000/postdata";

const int TCA_ADDR = 0x70; // I2C mux address
const int POLL_FREQUENCY_HZ = 100; // Frequency of IMU polling
const int POLL_INTERVAL_MS = 1000 / POLL_FREQUENCY_HZ;
const int POLLS_PER_FILE = 100; // Number of IMU measurements per file

int lastCompletedFile = -1; // Last file number that has been written and is ready to upload

void tcaSelect(uint8_t i);
void setupMPU6050();
void readMPU6050(int16_t* Ax, int16_t* Ay, int16_t* Az, int16_t* Gx, int16_t* Gy, int16_t* Gz);
void dataLogger(void * parameter);
void fileUploader(void * parameter);
void wipeSPIFFS();
void initializeWifi();
void readData(void * parameter);
void uploadData(void * parameter);

void setup() {
    Serial.begin(115200); // Serial communication baud rate
    Wire.begin(8, 9); // Pins for I2C communication to TCA (SDA, SCL)
    Wire.setClock(400000); // I2C Clock speed (400 kHz)

    // Initialize SPIFFS
    if (!SPIFFS.begin(true)) {
        Serial.println("SPIFFS Mount Failed");
        return;
    }
    Serial.println("SPIFFS Mount Success");

    // Wipe the SPIFFS
    wipeSPIFFS();

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

void wipeSPIFFS() {
    Serial.println("Wiping SPIFFS");
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

void readData(void * parameter) {
    TickType_t xLastWakeTime;
    const TickType_t xTimeIncrement = pdMS_TO_TICKS(POLL_INTERVAL_MS);
    
    File file;
    int pollCount = 0;
    int fileNumber = 0;
    
    xLastWakeTime = xTaskGetTickCount();

    while (1) {
        vTaskDelayUntil(&xLastWakeTime, xTimeIncrement);

        if (!file) {
            String fileName = "/" + String(fileNumber) + ".bin";
            file = SPIFFS.open(fileName, FILE_WRITE);
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

        if (pollCount >= POLLS_PER_FILE) {
            file.close();
            Serial.println("Finished writing to file: /" + String(fileNumber) + ".bin");
            lastCompletedFile = fileNumber;
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
            File fileToUpload = SPIFFS.open(fileName, FILE_READ);
            if (!fileToUpload) {
                Serial.println("Failed to open file for uploading");
            } else {
                Serial.println("Uploading file: " + fileName);
                if(WiFi.status() == WL_CONNECTED) {
                    HTTPClient http;
                    http.begin(serverName);
                    http.addHeader("Content-Type", "multipart/form-data; boundary=123456");

                    String preData = "--123456\r\nContent-Disposition: form-data; name=\"file\"; filename=\"";
                    preData += String(fileName) + "\"\r\nContent-Type: application/octet-stream\r\n\r\n";
                    String postData = "\r\n--123456--\r\n";

                    String fileData;
                    while(fileToUpload.available()) {
                        fileData += (char)fileToUpload.read();
                    }

                    size_t totalSize = preData.length() + fileData.length() + postData.length();
                    http.addHeader("Content-Length", String(totalSize));

                    int httpResponseCode = http.POST(preData + fileData + postData);

                    if(httpResponseCode >= 200 && httpResponseCode <= 299) {
                        String response = http.getString();
                        Serial.print("Upload successful: HTTP Code ");
                        Serial.println(httpResponseCode);
                        Serial.println(response);
                        lastUploadedFile++;
                    } else {
                        Serial.print("Error on sending POST: HTTP Code ");
                        Serial.println(httpResponseCode);
                        if (httpResponseCode > 0) {
                            String response = http.getString();
                            Serial.println(response);
                        }
                    }
                    http.end();
                } else {
                    Serial.println("Error in WiFi connection");
                }
                fileToUpload.close();
            }
        }
        vTaskDelay(pdMS_TO_TICKS(10));
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
    Wire.read(); Wire.read();
    *Gx = Wire.read() << 8 | Wire.read();
    *Gy = Wire.read() << 8 | Wire.read();
    *Gz = Wire.read() << 8 | Wire.read();
}

void initializeWifi() {
    Serial.println("\nConnecting to WiFi...");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected successfully");
    Serial.print("Assigned IP Address: ");
    Serial.println(WiFi.localIP());
}

void loop() {
    // Empty
}
