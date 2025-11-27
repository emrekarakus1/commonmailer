# Render PostgreSQL Veritabanı Kurulumu

## Problem
Render'da sunucu kapanıp açıldığında kullanıcı hesapları kayboluyor çünkü veriler geçici dosya sisteminde (ephemeral) tutuluyor.

## Çözüm
PostgreSQL veritabanı kullanarak verileri kalıcı hale getirmek.

---

## Adım 1: PostgreSQL Veritabanı Oluştur

1. **Render Dashboard'a Git**
   - https://dashboard.render.com adresine git
   - Login ol

2. **Yeni PostgreSQL Veritabanı Oluştur**
   - Sol menüden **"New +"** → **"PostgreSQL"** seç
   - **Name**: `commonportal-db` (veya istediğin isim)
   - **Database**: `commonportal` (otomatik doldurulabilir)
   - **User**: `commonportal_user` (otomatik doldurulabilir)
   - **Region**: Sunucunla aynı region'ı seç (ör: Frankfurt, US East)
   - **PostgreSQL Version**: En son stabil versiyonu seç (14 veya 15)
   - **Plan**: Free plan yeterli (küçük uygulamalar için)
   - **"Create Database"** butonuna tıkla

3. **Veritabanı Oluşturuluyor...**
   - 1-2 dakika bekle
   - Veritabanı hazır olduğunda yeşil "Available" durumunu göreceksin

---

## Adım 2: DATABASE_URL'i Web Servisine Bağla

1. **Web Servisini Bul**
   - Dashboard'da **commonmailer** (veya web servisin) servisini bul
   - Servise tıkla

2. **Environment Variables'a Git**
   - **"Environment"** sekmesine git
   - **"Environment Variables"** bölümünü bul

3. **DATABASE_URL'i Kopyala**
   - PostgreSQL veritabanının sayfasına git
   - **"Connections"** sekmesine git
   - **"Internal Database URL"** değerini kopyala
   - Örnek format: `postgresql://username:password@hostname:5432/database_name`

4. **DATABASE_URL'i Web Servisine Ekle**
   - Web servisinin **Environment** sekmesine geri dön
   - **"Add Environment Variable"** butonuna tıkla
   - **Key**: `DATABASE_URL`
   - **Value**: Kopyaladığın Internal Database URL'i yapıştır
   - **"Save Changes"** butonuna tıkla

---

## Adım 3: Servisi Yeniden Başlat

1. **Manuel Deploy Yap**
   - Web servisinin sayfasında **"Manual Deploy"** butonuna tıkla
   - **"Deploy latest commit"** seçeneğini seç
   - Deploy işlemini bekle (2-5 dakika)

2. **Logları Kontrol Et**
   - **"Logs"** sekmesine git
   - Şu mesajları görmelisin:
     ```
     Using PostgreSQL database from DATABASE_URL
     Running database migrations...
     Starting Gunicorn server...
     ```

---

## Adım 4: Doğrulama

1. **Veritabanı Bağlantısını Kontrol Et**
   - Uygulama açıldığında hata almamalısın
   - Eğer hata alırsan, Logs sekmesinden hata mesajını kontrol et

2. **Kullanıcı Kaydı Yap**
   - Uygulamaya git
   - Yeni bir kullanıcı kaydet
   - Logout yap

3. **Sunucuyu Yeniden Başlat (Test)**
   - Render Dashboard'da web servisinin **"Settings"** sekmesine git
   - **"Manual Deploy"** → **"Deploy latest commit"** yaparak sunucuyu yeniden başlat
   - VEYA sunucuyu birkaç saat beklet (Render free plan'da inaktiflikten sonra kapanır)

4. **Kullanıcı Hala Var mı Kontrol Et**
   - Uygulamaya tekrar gir
   - Login yapmayı dene - kullanıcı hala olmalı!
   - ✅ **BAŞARILI!** Artık veriler kalıcı.

---

## Sorun Giderme

### "DATABASE_URL environment variable is required" Hatası

**Problem**: DATABASE_URL ortam değişkeni ayarlanmamış.

**Çözüm**:
1. Web servisinin **Environment** sekmesine git
2. `DATABASE_URL` değişkeninin olup olmadığını kontrol et
3. Yoksa yukarıdaki Adım 2'yi takip et

### "Migration failed" Hatası

**Problem**: Veritabanı migration'ları çalışmıyor.

**Çözüm**:
1. Render Shell'i aç (Web servis → Shell)
2. Manuel olarak migration çalıştır:
   ```bash
   python manage.py migrate
   ```
3. Hata devam ederse, logları kontrol et

### "Database connection check failed" Hatası

**Problem**: Veritabanına bağlanılamıyor.

**Çözüm**:
1. PostgreSQL veritabanının durumunu kontrol et (Available olmalı)
2. DATABASE_URL'in doğru olduğundan emin ol (Internal Database URL kullan)
3. Web servis ile PostgreSQL veritabanı aynı region'da olmalı
4. PostgreSQL veritabanının **"Internal Database URL"** kullandığından emin ol (External Database URL değil)

### Kullanıcılar Hala Kayboluyor

**Problem**: DATABASE_URL ayarlanmış ama veriler hala kayboluyor.

**Kontrol Et**:
1. Logları kontrol et - "Using PostgreSQL database" mesajını görmelisin
2. SQLite kullanılıyor olabilir - bu durumda settings.py hatası olur
3. Veritabanı bağlantısı çalışıyor mu kontrol et:
   - Render Shell'den: `python manage.py dbshell`
   - Bu komut PostgreSQL'e bağlanmalı, SQLite shell açmamalı

---

## ⚠️ ÖNEMLİ: Veritabanı Silinme Sorunu

**Render'ın free PostgreSQL planında, 90 gün boyunca kullanılmayan veritabanları otomatik olarak silinir!**

Bu sorunu çözmek için **RENDER_DATABASE_KEEP_ALIVE.md** dosyasındaki talimatları takip edin.

**Hızlı Çözüm**: Render'da bir Cron Job oluşturun:
- Schedule: `*/30 * * * *` (her 30 dakikada bir)
- Command: `python manage.py keep_database_alive`
- Detaylar için: `RENDER_DATABASE_KEEP_ALIVE.md` dosyasına bakın

---

## Notlar

- **Free Plan Sınırlamaları**: Render'ın free PostgreSQL planında:
  - ⚠️ **90 gün inaktiflikten sonra veritabanı silinebilir** - Bu yüzden keep-alive kurulumu şarttır!
  - Küçük veri limiti (yaklaşık 1GB)
  - Bu uygulama için yeterli olmalı

- **Veritabanını Aktif Tutma**: 
  - **RENDER_DATABASE_KEEP_ALIVE.md** dosyasındaki talimatları okuyun
  - Render Cron Job ile otomatik keep-alive kurulumu yapın
  - Veya harici bir servis (UptimeRobot, vb.) ile `/healthz/` endpoint'ini periyodik çağırın

- **Backup**: Free plan'da otomatik backup yok. Önemli veriler için:
  - Render Shell'den: `python manage.py dumpdata > backup.json`
  - Veya: `python manage.py backup_user_data`
  - Bu dosyayı indirip güvenli bir yerde sakla

- **Internal vs External URL**: 
  - **Internal Database URL**: Render servisleri arasında kullanılır (hızlı ve güvenli)
  - **External Database URL**: Dışarıdan bağlantı için (genelde gereksiz)
  - **Her zaman Internal Database URL kullan!**

---

## Özet

✅ PostgreSQL veritabanı oluştur
✅ DATABASE_URL'i web servisine ekle
✅ Servisi yeniden deploy et
✅ Kullanıcı kaydı yap ve test et

Artık veriler kalıcı olacak! 🎉


