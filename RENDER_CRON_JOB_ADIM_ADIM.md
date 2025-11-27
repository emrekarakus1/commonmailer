# Render Cron Job Kurulumu - Adım Adım Rehber

## 🎯 Sorularınızın Cevapları

### 1. DATABASE_URL'i Nerede Bulacaksınız?

**İki yöntem var:**

#### Yöntem A: PostgreSQL Veritabanı Sayfasından (EN KOLAY)

1. Render Dashboard'da (https://dashboard.render.com) giriş yapın
2. Sol menüden **PostgreSQL veritabanınızı** bulun (örn: `commonportal-db`)
3. Veritabanına **tıklayın**
4. Sayfanın **üst kısmında** şu sekmeleri göreceksiniz:
   ```
   Overview | Connections | Settings | Logs | ...
   ```
5. **"Connections"** sekmesine tıklayın
6. **"Internal Database URL"** yazısının altındaki değeri kopyalayın
   - Format: `postgresql://kullanici:şifre@hostname:5432/veritabani`
   - ⚠️ **ÖNEMLİ**: "External Database URL" değil, **"Internal Database URL"** kopyalayın!

#### Yöntem B: Web Servisinden

1. Render Dashboard'da **Web servisinizi** bulun (örn: `commonmailer`)
2. Web servisine **tıklayın**
3. Sayfanın **üst kısmında** şu sekmeleri göreceksiniz:
   ```
   Overview | Environment | Logs | Settings | ...
   ```
4. **"Environment"** sekmesine tıklayın
5. **"Environment Variables"** listesinde `DATABASE_URL` değerini bulun
6. Değeri kopyalayın

---

### 2. Environment Variables Nereye Yazılacak?

**ÖNEMLİ**: Environment Variables'ları Cron Job **oluşturulduktan SONRA** ekliyorsunuz!

#### Adımlar:

1. **Cron Job'u Oluşturun** (öncelikle bunu yapın)
   - "New +" → "Cron Job" → Ayarları doldurun → "Create Cron Job"

2. **Cron Job Sayfasına Gidin**
   - Cron Job oluşturulduktan sonra otomatik olarak sayfaya yönlendirileceksiniz
   - Ya da Dashboard'dan Cron Job'unuzu bulup tıklayın

3. **Environment Sekmesini Bulun**
   - Cron Job sayfasının **üst kısmında** şu sekmeler var:
   ```
   Overview | Environment | Logs | Settings | ...
   ```
   - **"Environment"** sekmesine tıklayın

4. **Environment Variables Ekleme**
   - Sayfada **"Environment Variables"** başlığını görürsünüz
   - **"+ Add Environment Variable"** veya **"+"** butonuna tıklayın
   - **Key**: `DATABASE_URL` yazın
   - **Value**: Daha önce kopyaladığınız DATABASE_URL değerini yapıştırın
   - **"Save"** butonuna tıklayın

**Görsel Örnek:**
```
┌─────────────────────────────────────────────────┐
│ keep-database-alive                        [×] │
├─────────────────────────────────────────────────┤
│ Overview | Environment | Logs | Settings        │ ← Burada "Environment" tıkla
├─────────────────────────────────────────────────┤
│                                                 │
│ Environment Variables                           │
│                                                 │
│ ┌──────────────┬─────────────────────────────┐ │
│ │ Key          │ Value                       │ │
│ ├──────────────┼─────────────────────────────┤ │
│ │ DATABASE_URL │ postgresql://user:pass@...  │ │ ← Buraya eklenmiş
│ └──────────────┴─────────────────────────────┘ │
│                                                 │
│ [+ Add Environment Variable]                    │ ← Bu butona tıkla
│                                                 │
└─────────────────────────────────────────────────┘
```

---

### 3. Command Çalışma Dizini

**Cevap**: Command otomatik olarak projenin root dizininde (manage.py'nin olduğu yer) çalışır.

#### Ne Yazmalısınız:

**Command alanına sadece şunu yazın:**
```
python manage.py keep_database_alive
```

#### Neden Bu Kadar Basit?

- Render, Cron Job'ları **Web Service ile aynı dizinde** çalıştırır
- Web Service'iniz zaten `manage.py` dosyasının olduğu dizinde çalışıyor
- Bu yüzden ekstra `cd` komutuna gerek yok

**YANLIŞ Örnekler (yazmayın):**
```
cd /app && python manage.py keep_database_alive
python /app/manage.py keep_database_alive
cd /app/path/to/project && python manage.py keep_database_alive
```

**DOĞRU:**
```
python manage.py keep_database_alive
```

---

## 📋 Tam Kurulum Adımları (Özet)

### Adım 1: DATABASE_URL'i Kopyalayın
1. PostgreSQL veritabanınızın sayfasına gidin
2. "Connections" sekmesine tıklayın
3. "Internal Database URL" değerini kopyalayın

### Adım 2: Cron Job Oluşturun
1. Dashboard'da "New +" → "Cron Job"
2. Ayarları doldurun:
   - Name: `keep-database-alive`
   - Schedule: `*/30 * * * *`
   - Command: `python manage.py keep_database_alive`
   - Service: Web servisinizi seçin
   - Region: Web servisiyle aynı
   - Plan: Free
3. "Create Cron Job" butonuna tıklayın

### Adım 3: Environment Variables Ekleyin
1. Cron Job sayfasında "Environment" sekmesine gidin
2. "+ Add Environment Variable" butonuna tıklayın
3. Key: `DATABASE_URL`
4. Value: Kopyaladığınız DATABASE_URL değerini yapıştırın
5. "Save" butonuna tıklayın

### Adım 4: Test Edin
1. Cron Job sayfasında "Manual Trigger" butonuna tıklayın
2. "Logs" sekmesine gidin
3. Şu mesajı görmelisiniz: `✓ Database connection is alive`

---

## ❓ Sık Sorulan Sorular

**S: Environment sekmesini göremiyorum.**
C: Cron Job'u önce oluşturmanız gerekiyor. "Create Cron Job" butonuna tıkladıktan sonra Environment sekmesi görünecek.

**S: DATABASE_URL'i nereden bulacağım?**
C: PostgreSQL veritabanınızın sayfasına gidin → "Connections" sekmesi → "Internal Database URL"

**S: Command çalışmıyor.**
C: Command alanına sadece `python manage.py keep_database_alive` yazın. Başka bir şey eklemeyin.

**S: Environment variables ekledim ama çalışmıyor.**
C: DATABASE_URL'in doğru kopyalandığından emin olun. "Internal Database URL" kullanmalısınız, "External" değil.

---

## 🎉 Başarı!

Eğer tüm adımları tamamladıysanız:
- ✅ Cron Job her 30 dakikada bir çalışacak
- ✅ Veritabanınız aktif kalacak
- ✅ 90 gün kuralı artık sorun olmayacak

Sorunuz varsa logları kontrol edin: Cron Job → "Logs" sekmesi

