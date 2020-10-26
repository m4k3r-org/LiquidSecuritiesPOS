#include <M5ez.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

HTTPClient http;

void balance_amount(String asset) {
  http.begin("http://192.168.8.215:80/balance?asset="+asset);
  int httpResponseCode = http.GET();
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);
    
    StaticJsonDocument<1000> http_root;
    DeserializationError http_error = deserializeJson(http_root, response);
    if (error) {
      Serial.println(F("Failed to read json from block explorer"));
    }
    ez.msgBox("Balance", " "+http_root["result"]["asset"].as<String>()+": "+http_root["result"]["amount"].as<String>()+" sats.", "OK", true);
  }

}

void balance() {
  while(true){
    ezMenu submenu("Balance");
    submenu.txtSmall();
    submenu.buttons("up#Back#select##down#");
    http.begin("http://192.168.8.215:80/balance");
    int httpResponseCode = http.GET();
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println(response);
      
      StaticJsonDocument<1000> http_root;
      DeserializationError http_error = deserializeJson(http_root, response);
      if (error) {
        Serial.println(F("Failed to read json from block explorer"));
      }
  
      JsonArray array = http_root["result"].as<JsonArray>();
      for (JsonVariant v : array){
          Serial.println(v.as<String>());
          submenu.addItem(v.as<String>());
      }
  
    }
    submenu.addItem("Go back to main menu");
    submenu.runOnce();
    if (submenu.pickName() == "Go back to main menu") {
      break;
    } else {
      balance_amount(submenu.pickName());
    }
  }
}

void gaid() {
  ez.msgBox("GAID", "", "Done", false);
  //ez.buttons.show("Done");
  http.begin("http://192.168.8.215:80/gaid");
  int httpResponseCode = http.GET();
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);
    
    StaticJsonDocument<1000> http_root;
    DeserializationError http_error = deserializeJson(http_root, response);
    if (error) {
      Serial.println(F("Failed to read json from block explorer"));
    }
    M5.Lcd.qrcode( http_root["result"].as<String>(), 60, 10, 200, 6);
  }
  while (true) {
    String btnpressed = ez.buttons.poll();
    if (btnpressed == "Done") break;
  }
}

boolean isValidNumber(String str){
   for(byte i=0;i<str.length();i++)
   {
      if(isDigit(str.charAt(i))) return true;
        }
   return false;
}

void receivepayment() {
  String name = ez.textInput("Payment name or id","");

  String asset = "";
  ezMenu submenu("Select asset");
  submenu.txtSmall();
  submenu.buttons("up#Back#select##down#");
  http.begin("http://192.168.8.215:80/assets");
  int httpResponseCode = http.GET();
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);
    
    StaticJsonDocument<1000> http_root;
    DeserializationError http_error = deserializeJson(http_root, response);
    if (error) {
      Serial.println(F("Failed to read json from block explorer"));
    }

    JsonArray array = http_root["result"].as<JsonArray>();
    for (JsonVariant v : array){
        Serial.println(v["id"].as<String>());
        submenu.addItem(v["id"].as<String>());
    }

  }
  submenu.addItem("Exit | Go back to main menu");
  submenu.runOnce();
  if (submenu.pickName() == "Go back to main menu") {
    return;
  } else {
    asset = submenu.pickName();
  }

  int amount = 0;
  while(true){
    String amount_str = ez.textInput("Amount","");
    if (isValidNumber(amount_str)) {
      amount = amount_str.toInt();
      break;
    }
  }
  
  ez.buttons.show("Wait | Done");
  http.begin(String("http://192.168.8.215:80")+"/address"+"?name="+name+"&asset="+asset+"&amount="+amount);
  httpResponseCode = http.GET();
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);
    
    StaticJsonDocument<1000> http_root;
    DeserializationError http_error = deserializeJson(http_root, response);
    if (error) {
      Serial.println(F("Failed to read json from block explorer"));
    }
    M5.Lcd.qrcode( http_root["result"]["address"].as<String>(), 60, 10, 200, 6);
  }
  while (true) {
    String btnpressed = ez.buttons.poll();
    if (btnpressed == "Done") break; 
  }

  /*String btnpressed = ez.buttons.poll();
  if (btnpressed == "Done") break;
  
  http.begin(String("http://192.168.8.215:80")+"/check"+"?pointer="+pointer);
  httpResponseCode = http.GET();
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);

    StaticJsonDocument<1000> http_root;
    DeserializationError http_error = deserializeJson(http_root, response);
    if (error) {
      Serial.println(F("Failed to read json from check call"));
    }*/
}


void receiveaddr() {
  ez.buttons.show("Wait | Done");
  http.begin("http://192.168.8.215:80/address");
  int httpResponseCode = http.GET();
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println(response);
    
    StaticJsonDocument<1000> http_root;
    DeserializationError http_error = deserializeJson(http_root, response);
    if (error) {
      Serial.println(F("Failed to read json from block explorer"));
    }
    M5.Lcd.qrcode( http_root["result"].as<String>(), 60, 10, 200, 6);
  
    String pointer = http_root["result"]["pointer"].as<String>();
    bool wait_for_payment = false;
    while (true) {
      String btnpressed = ez.buttons.poll();
      if (btnpressed == "Done") break;
      if (btnpressed == "Wait") {
         wait_for_payment = true;
         break;
      }
    }

    // wait for payment
    while (wait_for_payment){
      http.begin(String("http://192.168.8.215:80")+"/check"+"?pointer="+pointer);
      httpResponseCode = http.GET();
      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println(response);
    
        StaticJsonDocument<1000> http_root;
        DeserializationError http_error = deserializeJson(http_root, response);
        if (error) {
          Serial.println(F("Failed to read json from check call"));
        }
        ez.msgBox("Wait for payment", http_root["result"], "OK", false);
        if (http_root["result"] == "PAYED") {
          delay(10000);
          break;
        }
        if (http_root["result"] == "PARTIALLY PAYED"){
          delay(10000);
          break;
        }
      }  
      delay(1000);
    }
  }
}

void about(){
   ez.textBox("About", "", true, "up#Done#down");
}

void setup() {
  #include <themes/default.h>
  #include <themes/dark.h>
  ezt::setDebug(INFO);
  ez.begin();
  http.setReuse(true);
  //M5.Lcd.pushImage(0, 0, 320, 240, (uint16_t *)pixel_data);
  delay(1000);
}

void loop() {
  ezMenu mainmenu("Blockstream AMP");
  mainmenu.txtSmall();
  mainmenu.addItem("Balance", balance);
  mainmenu.addItem("Receive payment", receivepayment);
  mainmenu.addItem("Receiving address", receiveaddr);
  mainmenu.addItem("Check payments");
  mainmenu.addItem("My GAID", gaid);
  mainmenu.addItem("");
  mainmenu.addItem("About", about);
  mainmenu.addItem("Built-in wifi & other settings", ez.settings.menu);
  mainmenu.upOnFirst("last|up");
  mainmenu.downOnLast("first|down");
  mainmenu.run();
}
