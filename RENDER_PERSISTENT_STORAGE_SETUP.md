# Render Persistent Storage Kurulum Rehberi

## 🎯 Amaç

Bu rehber, Render'da template'lerin ve kullanıcı verilerinin kalıcı olarak saklanması için gerekli adımları açıklar.

## ⚠️ Mevcut Sorun

**PROBLEM:** Render'da her deployment'ta container yeniden oluşuyor ve geçici dosya sistemi kullanılıyor. Bu yüzden:
- ❌ Template'ler kayboluyor
- ❌ Kullanıcı verileri siliniyor
- ❌ 1 hafta sonra tekrar giriş yapınca template'ler yok

**ÇÖZÜM:** Render Persistent Volume (Disk) kullanarak verileri kalıcı disk'te saklamak.

## 📋 Adım Adım Kurulum

### Adım 1: Render Dashboard'a Git

1. https://dashboard.render.com adresine git
2. Login ol
3. Dashboard'da mevcut servislerinizi görün

### Adım 2: Persistent Disk Oluştur

1. **"New +"** butonuna tıkla
2. **"Disk"** seçeneğini seç
3. Disk ayarlarını yap:
   - **Name:** `commonmailer-data` (veya istediğiniz isim)
   - **Mount Path:** `/app/persistent_data` ⚠️ **ÖNEMLİ: Bu path'i aynen kullanın**
   - **Size:** 1GB (ücretsiz plan için yeterli)
   - **Region:** Web service'inizle aynı region'ı seçin
4. **"Create Disk"** butonuna tıkla

### Adım 3: Disk'i Web Service'e Bağla

1. Web service'inizin sayfasına git (commonmailer)
2. **"Settings"** sekmesine tıkla
3. **"Disks"** bölümünü bul
4. **"Attach Disk"** butonuna tıkla
5. Oluşturduğunuz disk'i seç (`commonmailer-data`)
6. **"Attach"** butonuna tıkla

### Adım 4: Environment Variables Ekle

1. Web service'inizin **"Settings"** sekmesinde
2. **"Environment"** bölümüne git
3. Şu environment variables'ları ekle:

```env
DATA_STORAGE_PATH=/app/persistent_data
USER_TEMPLATES_PATH=/app/persistent_data/user_templates
EMAIL_TEMPLATES_PATH=/app/persistent_data/email_templates.json
```

**ÖNEMLİ:** 
- Path'ler **mutlaka** `/app/persistent_data` ile başlamalı
- Bu path'ler disk'in mount path'i ile eşleşmeli

### Adım 5: Deploy Et

1. Environment variables'ları ekledikten sonra **"Save Changes"** tıkla
2. Otomatik deploy başlayacak
3. Deploy tamamlanmasını bekle (2-5 dakika)

### Adım 6: Kontrol Et

Deploy tamamlandıktan sonra:

1. Render Shell'i aç (Web service → Shell)
2. Şu komutu çalıştır:
```bash
python manage.py check_storage
```

Bu komut şunları kontrol eder:
- ✅ Storage path'lerin doğru olduğunu
- ✅ Disk'in mount edildiğini
- ✅ Yazma izinlerini
- ✅ Mevcut template'leri

## 🧪 Test Senaryosu

1. ✅ Persistent disk kuruldu
2. ✅ Environment variables eklendi
3. ✅ Deploy tamamlandı
4. **Test:**
   - Hesap oluştur
   - Template kaydet
   - Çıkış yap
   - 1 hafta sonra tekrar giriş yap
   - Template'lerin hala orada olduğunu kontrol et

## 📊 Veri Yapısı

Kurulumdan sonra disk'te şu yapı oluşur:

```
/app/persistent_data/
├── user_templates/
│   ├── email_templates_user_1.json
│   ├── email_templates_user_2.json
│   └── email_templates_user_3.json
├── email_templates.json
└── backups/
    └── user_1/
        ├── backup_2024-01-15_10-30-00.json
        └── backup_2024-01-16_14-20-00.json
```

## 🔍 Sorun Giderme

### Template'ler görünmüyor

1. **Storage path kontrolü:**
   ```bash
   python manage.py check_storage
   ```

2. **Disk mount kontrolü:**
   - Render Dashboard → Disk → "Mounts" sekmesi
   - Disk'in web service'e bağlı olduğunu kontrol et

3. **Environment variables kontrolü:**
   - Settings → Environment
   - `DATA_STORAGE_PATH=/app/persistent_data` olduğundan emin ol

### Disk yazma hatası

1. **Yazma izinleri:**
   ```bash
   ls -la /app/persistent_data
   ```

2. **Disk boyutu:**
   - Dashboard → Disk → "Usage" kontrol et
   - 1GB'dan fazla kullanılıyorsa disk boyutunu artır

### Deployment sonrası veriler kayboldu

1. **Disk bağlantısı:** Disk'in web service'e bağlı olduğunu kontrol et
2. **Path kontrolü:** Environment variables'ların doğru olduğunu kontrol et
3. **Mount path:** `/app/persistent_data` olduğundan emin ol

## 📝 Önemli Notlar

1. **Disk Silinirse:** Disk silinirse tüm veriler kaybolur! Dikkatli olun.
2. **Backup:** Render disk'leri otomatik backup almaz. Manuel backup yapın.
3. **Region:** Disk ve web service aynı region'da olmalı.
4. **Path:** Mount path `/app/persistent_data` olmalı, değiştirmeyin.

## ✅ Başarı Kriterleri

Kurulum başarılı olduğunda:
- ✅ `python manage.py check_storage` komutu başarılı çalışır
- ✅ Template'ler kaydedilir ve kalıcı olur
- ✅ 1 hafta sonra template'ler hala orada
- ✅ Her deployment'ta veriler korunur

## 🆘 Yardım

Sorun yaşarsanız:
1. Render Dashboard → Logs sekmesinden hataları kontrol edin
2. `python manage.py check_storage` komutunu çalıştırın
3. Environment variables'ları tekrar kontrol edin

