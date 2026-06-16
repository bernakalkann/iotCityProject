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
try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Hata: 'paho-mqtt' kütüphanesi bulunamadı.")
    print("Lütfen terminalde şu komutu çalıştırın: pip install paho-mqtt")
    sys.exit(1)

# Canlı Grafik için 'matplotlib' kütüphanesi kullanılmaktadır.
try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Hata: 'matplotlib' kütüphanesi bulunamadı.")
    print("Lütfen terminalde şu komutu çalıştırın: pip install matplotlib")
    sys.exit(1)

# --- CANLI GRAFİK VERİ YAPILARI ---
times = []
temperatures = []
humidities = []
MAX_DATA_POINTS = 30

fig = None
ax_temp = None
ax_hum = None
line_temp = None
line_hum = None


def init_plot():
    """
    Matplotlib grafik penceresini ve alt grafikleri interaktif modda ilklendirir.
    """
    global fig, ax_temp, ax_hum, line_temp, line_hum
    if fig is not None:
        return
    try:
        # İnteraktif modu aktif et (grafiğin donmaması ve arka planda güncellenebilmesi için)
        plt.ion()
        fig, (ax_temp, ax_hum) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
        fig.canvas.manager.set_window_title('Akıllı Şehir IoT Sensör Simülatörü')

        line_temp, = ax_temp.plot([], [], 'r-o', label='Sıcaklık (°C)')
        line_hum, = ax_hum.plot([], [], 'b-o', label='Nem (%)')

        ax_temp.set_ylabel('Sıcaklık (°C)')
        ax_temp.grid(True)
        ax_temp.legend(loc='upper left')

        ax_hum.set_ylabel('Nem (%)')
        ax_hum.set_xlabel('Zaman (Adım)')
        ax_hum.grid(True)
        ax_hum.legend(loc='upper left')

        plt.tight_layout()
    except Exception as e:
        print(f"Grafik arayüzü başlatılamadı (Muhtemelen GUI desteği olmayan bir ortamdasınız): {e}")


def update_plot(sicaklik, nem):
    """
    Sıcaklık ve nem verileriyle grafiği anlık olarak günceller.
    Sıcaklık 35 dereceyi geçtiğinde görsel uyarı verir.
    """
    global fig, ax_temp, ax_hum, line_temp, line_hum, times, temperatures, humidities
    if fig is None:
        return
        
    try:
        # Grafik penceresinin açık olup olmadığını kontrol edelim
        if not plt.fignum_exists(fig.number):
            return
            
        # Verileri listeye ekle
        if len(times) == 0:
            times.append(1)
        else:
            times.append(times[-1] + 1)
            
        temperatures.append(sicaklik)
        humidities.append(nem)
        
        # Son MAX_DATA_POINTS adet veriyi tut
        if len(times) > MAX_DATA_POINTS:
            times.pop(0)
            temperatures.pop(0)
            humidities.pop(0)
            
        # Verileri güncelle
        line_temp.set_data(times, temperatures)
        line_hum.set_data(times, humidities)
        
        # Eksen sınırlarını ayarla
        ax_temp.relim()
        ax_temp.autoscale_view()
        ax_hum.relim()
        ax_hum.autoscale_view()
        
        # X eksenini kaydır
        ax_temp.set_xlim(min(times), max(times))
        
        # Görsel Uyarı: Sıcaklık 35 dereceyi geçtiğinde
        if sicaklik > 35:
            fig.suptitle(f"⚠️ KRİTİK EŞİK AŞILDI! Sıcaklık: {sicaklik}°C ⚠️", color='red', fontsize=14, fontweight='bold')
            ax_temp.set_facecolor('#ffe6e6') # Hafif kırmızı arka plan
        else:
            fig.suptitle("Akıllı Şehir IoT Sensör İzleme Paneli", color='green', fontsize=14, fontweight='bold')
            ax_temp.set_facecolor('#ffffff') # Normal beyaz arka plan
            
        fig.canvas.draw()
        fig.canvas.flush_events()
    except Exception:
        # Grafik kapatılırsa veya çizilemezse sessizce devam et
        pass

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

    # Grafiği ilklendir
    init_plot()

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
            
            # Grafiği güncelle
            update_plot(data["sicaklik"], data["nem"])
            
            # Bekleme ve grafik güncelleme (plt.pause hem bekler hem de grafik pencerelerini açık tutar)
            if fig is not None and plt.fignum_exists(fig.number):
                plt.pause(2.0)
            else:
                time.sleep(2.0)
            
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
    
    # Grafiği ilklendir
    init_plot()
    
    try:
        while True:
            data = generate_sensor_data()
            print(f"[Simüle Edilen Veri]: {json.dumps(data)}")
            # Sıcaklık 35 dereceyi geçtiğinde terminalde uyarı gösterelim (Lambda'ya benzer şekilde)
            if data["sicaklik"] > 35:
                print("🚨 UYARI: Sıcaklık kritik seviyede! (>35°C)")
            
            # Grafiği güncelle
            update_plot(data["sicaklik"], data["nem"])
            
            # Bekleme ve grafik güncelleme
            if fig is not None and plt.fignum_exists(fig.number):
                plt.pause(2.0)
            else:
                time.sleep(2.0)
    except KeyboardInterrupt:
        print("\nYerel simülasyon sonlandırıldı.")


if __name__ == "__main__":
    main()
