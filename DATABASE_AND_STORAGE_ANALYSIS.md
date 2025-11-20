# Veritabanı ve Veri Depolama Analizi

## 📊 Mevcut Durum Analizi

### 1. Veritabanı Yapısı

**✅ İYİ: Kullanıcılar Ayrı Tutuluyor**
- Tek bir PostgreSQL veritabanı kullanılıyor (Render'da)
- Django'nun `User` modeli ile her kullanıcı ayrı kayıt olarak tutuluyor
- Her kullanıcının kendi `id`'si var
- Kullanıcılar birbirinin verilerine erişemiyor (Django authentication sistemi)

**Nasıl Çalışıyor:**
```python
# Her kullanıcı için ayrı User kaydı
User.objects.create_user(username=..., email=..., password=...)
# User.id ile kullanıcılar birbirinden ayrılıyor
```

### 2. Template Depolama

**✅ İYİ: Kullanıcı Bazlı Dosya Sistemi**
- Her kullanıcı için ayrı dosya: `email_templates_user_{user_id}.json`
- Dosyalar `USER_TEMPLATES_PATH` klasöründe tutuluyor
- Kullanıcılar birbirinin template'lerini göremez

**Dosya Yapısı:**
```
persistent_data/
  └── user_templates/
      ├── email_templates_user_1.json  (Kullanıcı 1'in template'leri)
      ├── email_templates_user_2.json  (Kullanıcı 2'nin template'leri)
      └── email_templates_user_3.json  (Kullanıcı 3'ün template'leri)
```

### 3. ⚠️ SORUN: Render'da Veri Kalıcılığı

**PROBLEM:**
- Render'da container'lar geçici dosya sistemi kullanıyor
- Her deployment'ta container yeniden oluşuyor
- `BASE_DIR / "persistent_data"` klasörü her deployment'ta siliniyor
- **Template'ler kayboluyor!**

**ÇÖZÜM:**
- Render'da **Persistent Volume (Disk)** kullanılmalı
- Environment variable ile mount path belirtilmeli
- Veriler kalıcı disk'te saklanmalı

## 🔧 Yapılması Gerekenler

### 1. Render'da Persistent Volume Kurulumu

**Adımlar:**
1. Render Dashboard → "New +" → "Disk"
2. Disk ayarları:
   - **Name:** `commonmailer-data`
   - **Mount Path:** `/app/persistent_data`
   - **Size:** 1GB (ücretsiz plan)
   - **Region:** Web service ile aynı
3. Web service'e bağla:
   - Web service → Settings → Disks
   - "Attach Disk" → `commonmailer-data` seç

### 2. Environment Variables

Render'da web service'inizde şu environment variables'ları ekleyin:

```env
DATA_STORAGE_PATH=/app/persistent_data
USER_TEMPLATES_PATH=/app/persistent_data/user_templates
EMAIL_TEMPLATES_PATH=/app/persistent_data/email_templates.json
```

### 3. Kod Kontrolü

Kod zaten doğru yapılandırılmış:
- ✅ `settings.py`'da `DATA_STORAGE_PATH` environment variable'dan okunuyor
- ✅ `TemplateService` her kullanıcı için ayrı dosya kullanıyor
- ✅ `user_id` ile dosyalar ayrılıyor

## 📝 Özet

### ✅ İYİ OLAN KISIMLAR:
1. **Veritabanı:** Kullanıcılar ayrı tutuluyor (Django User modeli)
2. **Template Dosyaları:** Her kullanıcı için ayrı dosya
3. **Kod Yapısı:** User-specific data handling doğru

### ⚠️ DÜZELTİLMESİ GEREKEN:
1. **Render Persistent Volume:** Kurulmalı ve mount edilmeli
2. **Environment Variables:** Render'da ayarlanmalı
3. **Test:** 1 hafta sonra template'lerin durduğu kontrol edilmeli

## 🧪 Test Senaryosu

1. Render'da Persistent Volume kur
2. Environment variables'ları ekle
3. Deploy et
4. Hesap oluştur ve template kaydet
5. 1 hafta sonra tekrar giriş yap
6. Template'lerin hala orada olduğunu kontrol et

## 📚 Render Persistent Volume Hakkında

**Render'da Disk (Persistent Volume):**
- Render'ın ücretsiz planında 1GB disk alanı var
- Disk'ler container'lar arasında paylaşılabilir
- Disk'ler deployment'lardan sonra da kalır
- Mount path: `/app/persistent_data` (veya istediğiniz path)

**Önemli Notlar:**
- Disk'ler sadece aynı region'daki servislere bağlanabilir
- Disk'ler otomatik backup alınmaz (manuel backup gerekir)
- Disk'ler silinirse veriler kaybolur (dikkatli olun!)

