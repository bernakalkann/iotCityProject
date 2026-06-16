# -*- coding: utf-8 -*-
"""
Proje 7: IoT ve Akıllı Şehir Uygulaması - AWS Lambda Analiz Fonksiyonu (lambda_function.py)

Bu Python kodu AWS Lambda üzerinde çalışır. AWS IoT Core üzerinden tetiklenerek
gelen sensör verisini alır, analiz eder ve sıcaklık 35°C'yi geçtiğinde alarm üretir.
"""

import json
import logging

# AWS CloudWatch logları için loglama yapılandırması
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda fonksiyonunun giriş noktası (Handler).
    
    :param event: AWS IoT Core kuralı tarafından iletilen tetikleyici veri (dict/JSON).
    :param context: Lambda çalışma zamanı (runtime) hakkında bilgi içeren nesne.
    :return: İşlem sonucunu gösteren yanıt sözlüğü.
    """
    logger.info("Gelen Ham Olay (Event) Verisi: %s", json.dumps(event))
    
    try:
        # 1. Gelen olay verisinden alanları ayıklama
        # IoT Rule veriyi doğrudan Python dict (sözlük) olarak Lambda'ya iletir.
        sensor_id = event.get("sensor_id", "Bilinmeyen-Sensor")
        timestamp = event.get("timestamp", 0)
        sicaklik = event.get("sicaklik")
        nem = event.get("nem")
        
        # Gerekli verilerin varlığını kontrol etme
        if sicaklik is None or nem is None:
            raise ValueError("Eksik veri: 'sicaklik' veya 'nem' alanı bulunamadı!")
            
        logger.info("Sensör: %s, Sıcaklık: %s°C, Nem: %%%s", sensor_id, sicaklik, nem)
        
        # 2. Analiz Aşaması: Sıcaklık Değerini Kontrol Etme
        alarm_uretiyorsa = False
        alarm_mesaji = ""
        
        if sicaklik > 35.0:
            alarm_uretiyorsa = True
            alarm_mesaji = f"🚨 UYARI: {sensor_id} isimli sensörde kritik sıcaklık tespit edildi! Sıcaklık: {sicaklik}°C"
            logger.warning("ALARM TETİKLENDİ: %s", alarm_mesaji)
            # Gerçek bir projede burada AWS SNS (Simple Notification Service) ile SMS veya E-posta
            # gönderilebilir ya da DynamoDB veritabanına alarm kaydı eklenebilir.
        else:
            logger.info("Sıcaklık normal sınırlar içerisinde (%s°C).", sicaklik)
            
        # 3. Yanıt Hazırlama
        response_body = {
            "mesaj": "Veri başarıyla işlendi.",
            "sensor_id": sensor_id,
            "sicaklik": sicaklik,
            "nem": nem,
            "alarm_durumu": "AKTIF" if alarm_uretiyorsa else "PASIF",
            "alarm_mesaji": alarm_mesaji
        }
        
        # Başarılı HTTP 200 benzeri durum kodu döner
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": response_body
        }
        
    except Exception as e:
        # Hata durumunda loglama yapıp hata bilgisi döndürme
        hata_mesaji = f"Veri işlenirken hata oluştu: {str(e)}"
        logger.error(hata_mesaji)
        
        return {
            "statusCode": 400,
            "body": {
                "mesaj": "Hata oluştu",
                "hata": hata_mesaji
            }
        }
