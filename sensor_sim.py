# -*- coding: utf-8 -*-
"""
Proje 7: IoT ve Akıllı Şehir Uygulaması - Sanal IoT Cihaz Simülatörü (sensor_sim.py)

Bu script, akıllı bir şehirdeki çevre sensörünü (Sıcaklık ve Nem) simüle eder.
Toplanan verileri JSON formatına dönüştürerek MQTT protokolü üzerinden güvenli bir şekilde
AWS IoT Core platformuna gönderir.
"""

import time
import json
import random
import ssl
import sys

# MQTT istemcisi için 'paho-mqtt' kütüphanesi kullanılmaktadır.
# Eğer yüklü değilse terminalden 'pip install paho-mqtt' komutuyla kurulabilir.
try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Hata: 'paho-mqtt' kütüphanesi bulunamadı.")
    print("Lütfen terminalde şu komutu çalıştırın: pip install paho-mqtt")
    sys.exit(1)

# --- AWS IoT CORE YAPILANDIRMASI ---
# NOT: AWS Management Console'dan edineceğiniz bilgileri buraya girmelisiniz.
AWS_ENDPOINT = "YOUR_AWS_IOT_ENDPOINT.iot.eu-west-1.amazonaws.com" # AWS IoT Core veri adresi (Endpoint)
CLIENT_ID = "AkilliSehir_Sensor_01"                              # AWS'de tanımlı benzersiz Thing (Nesne) adı
TOPIC = "sehir/sensor/veri"                                       # Verinin yayınlanacağı MQTT konusu (Topic)

# TLS/SSL Güvenlik Sertifikaları Yolları
# AWS IoT Core, sertifika tabanlı (X.509) karşılıklı kimlik doğrulaması (Mutual Auth) gerektirir.
CA_PATH = "certs/AmazonRootCA1.pem"           # Amazon Root CA 1 sertifikası
CERT_PATH = "certs/device-certificate.pem.crt" # Cihaz sertifikası (Certificate)
KEY_PATH = "certs/private.pem.key"            # Özel anahtar (Private Key)


def on_connect(client, userdata, flags, rc):
    """
    MQTT sunucusuna (AWS IoT Core) bağlantı kurulduğunda tetiklenen geri çağırma (callback) fonksiyonu.
    """
    if rc == 0:
        print("✓ AWS IoT Core'a başarıyla bağlanıldı!")
    else:
        print(f"✗ Bağlantı başarısız! Hata Kodu: {rc}")


def on_publish(client, userdata, mid):
    """
    Mesaj başarıyla yayınlandığında (publish edildiğinde) tetiklenen geri çağırma fonksiyonu.
    """
    print(f"→ Mesaj AWS IoT Core'a gönderildi. (Mesaj ID: {mid})")


def generate_sensor_data():
    """
    Sanal sensör verileri (Sıcaklık ve Nem) üretir.
    Akıllı şehir senaryosuna uygun olması için rastgele dalgalanmalar ekler.
    """
    # Sıcaklığı 15.0 ile 42.0 derece arasında rastgele simüle ederiz
    temperature = round(random.uniform(15.0, 42.0), 2)
    # Nemi %30 ile %85 arasında rastgele simüle ederiz
    humidity = round(random.uniform(30.0, 85.0), 2)
    
    # AWS Lambda tarafından işlenecek veri paketi (Payload)
    payload = {
        "sensor_id": CLIENT_ID,
        "timestamp": int(time.time()),
        "sicaklik": temperature,
        "nem": humidity,
        "durum": "NORMAL"
    }
    return payload


def main():
    # 1. Yeni bir MQTT istemcisi oluşturuyoruz.
    # MQTTv3.1.1 protokol sürümünü kullanması gerektiğini belirtiyoruz.
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

    # 2. Bağlantı ve yayınlama olayları için geri çağırma fonksiyonlarını atıyoruz.
    client.on_connect = on_connect
    client.on_publish = on_publish

    # 3. TLS / SSL Ayarları (AWS IoT Core zorunlu kılar)
    # AWS IoT Core 8883 portunu (Güvenli MQTT) kullanır.
    # Sertifikaları ve anahtarları tanımlayarak karşılıklı kimlik doğrulamayı (mutual TLS) aktif ediyoruz.
    try:
        client.tls_set(
            ca_certs=CA_PATH,
            certfile=CERT_PATH,
            keyfile=KEY_PATH,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLSv1_2,
            ciphers=None
        )
    except FileNotFoundError as e:
        print(f"\n⚠️ Sertifika dosyası bulunamadı: {e.filename}")
        print("AWS IoT Core'a bağlanmadan önce 'certs/' klasörüne sertifikalarınızı yerleştirmelisiniz.")
        print("Şimdilik kodun hata vermeden simülasyon çıktısı üretmesi için devam ediliyor...\n")
        # Gerçek bağlantı olmadan simülasyonu terminalde göstermek için yerel bir döngü başlatıyoruz:
        run_local_simulation()
        return

    # 4. AWS IoT Core Endpoint'ine bağlanma teşebbüsü
    # AWS IoT Core için standart MQTT TLS portu 8883'tür.
    print(f"Bağlanılıyor: {AWS_ENDPOINT} (Port: 8883)...")
    try:
        client.connect(AWS_ENDPOINT, 8883, keepalive=60)
    except Exception as e:
        print(f"✗ Bağlantı hatası: {e}")
        print("Lütfen AWS endpoint adresinizi ve ağ bağlantınızı kontrol edin.")
        print("Simülasyon moduna geçiliyor...\n")
        run_local_simulation()
        return

    # Arka planda MQTT ağ döngüsünü başlatıyoruz (bağlantıyı canlı tutmak ve paketleri işlemek için)
    client.loop_start()

    print("Sensör veri gönderimi başlatıldı. Durdurmak için Ctrl+C tuşlarına basın.")
    try:
        while True:
            # Sensör verisi üret
            data = generate_sensor_data()
            # JSON formatına çevir
            json_payload = json.dumps(data)
            
            print(f"\nYayınlanıyor -> Topic: {TOPIC}")
            print(f"Veri: {json_payload}")
            
            # Veriyi yayınla
            client.publish(TOPIC, json_payload, qos=1)
            
            # 5 saniye bekle
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nVeri gönderimi kullanıcı tarafından durduruldu.")
    finally:
        # Bağlantıyı düzgün bir şekilde kapat
        client.loop_stop()
        client.disconnect()
        print("AWS IoT Core bağlantısı kapatıldı.")


def run_local_simulation():
    """
    Sertifikalar veya endpoint eksik/hatalı olduğunda yerel simülasyon çıktısı üretir.
    Bu sayede AWS kurulumu tamamlanmadan da kodun çıktısı incelenebilir.
    """
    print("--- YEREL SİMÜLASYON MODU (AWS Bağlantısı Yok) ---")
    try:
        while True:
            data = generate_sensor_data()
            print(f"[Simüle Edilen Veri]: {json.dumps(data)}")
            # Sıcaklık 35 dereceyi geçtiğinde terminalde uyarı gösterelim (Lambda'ya benzer şekilde)
            if data["sicaklik"] > 35:
                print("🚨 UYARI: Sıcaklık kritik seviyede! (>35°C)")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nYerel simülasyon sonlandırıldı.")


if __name__ == "__main__":
    main()
