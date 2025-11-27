# Render Veritabanı Silinme Sorunu - Türkçe Açıklama

## Sorun

Render'da ücretsiz PostgreSQL veritabanı kullanırken, uygulamayı bir süre kullanmadığınızda veritabanı tamamen siliniyor. Bu durum şu sebeplerden kaynaklanır:

### Neden Oluyor?

1. **90 Gün Kuralı**: Render'ın ücretsiz PostgreSQL planında, veritabanı 90 gün boyunca hiç kullanılmazsa otomatik olarak silinir.

2. **Inaktivite**: Uygulamanızı kullanmadığınızda, veritabanına bağlantı yapılmaz ve Render bunu "kullanılmayan" olarak işaretler.

3. **Otomatik Temizlik**: Render, kullanılmayan kaynakları temizlemek için uzun süre aktif olmayan veritabanlarını siler.

## Çözüm

### ✅ Çözüm 1: Otomatik Keep-Alive (Önerilen)

Veritabanını aktif tutmak için periyodik olarak basit bir sorgu çalıştırın.

#### Nasıl Yapılır?

1. **Render Dashboard'a git**: https://dashboard.render.com
2. **Yeni Cron Job oluştur**:
   - Sol menüden "New +" → "Cron Job" seç
   - Name: `keep-database-alive`
   - Schedule: `*/30 * * * *` (her 30 dakikada bir)
   - Command: `python manage.py keep_database_alive`
   - Service: Web servisinizi seç
   - Region: Web servisiyle aynı region
   - Plan: Free
3. **Environment Variables ekle**:
   - `DATABASE_URL` (web servisinizden kopyalayın)
   - Diğer gerekli değişkenler
4. **Create Cron Job** butonuna tıklayın

#### Test

- Cron Job oluşturulduktan sonra "Manual Trigger" butonuna tıklayın
- "Logs" sekmesinde şu mesajı görmelisiniz: `✓ Database connection is alive`

Detaylı adımlar için: **RENDER_DATABASE_KEEP_ALIVE.md** dosyasına bakın.

---

### ✅ Çözüm 2: Health Check Endpoint'i Kullan

Uygulamanızda `/healthz/` endpoint'i var. Bu endpoint veritabanını test eder ve aktif tutar.

**Harici servis ile kullanım**:
- UptimeRobot (https://uptimerobot.com) gibi bir servis kullanın
- URL: `https://your-app.onrender.com/healthz/`
- Interval: 15-30 dakika
- Bu servis periyodik olarak endpoint'inizi çağıracak

---

### ✅ Çözüm 3: Ücretli Plan'e Geçiş

Render'ın ücretli PostgreSQL planı (Starter: $7/ay):
- ✅ Veritabanı asla silinmez
- ✅ Otomatik yedeklemeler
- ✅ Daha fazla depolama

---

## Hızlı Başlangıç

1. **RENDER_DATABASE_KEEP_ALIVE.md** dosyasını okuyun
2. Render'da bir Cron Job oluşturun (yukarıdaki Çözüm 1)
3. Veritabanınız artık aktif kalacak! ✅

## Önemli Notlar

- ⚠️ **90 gün kuralı**: Free plan'da 90 gün inaktiflikten sonra veritabanı silinir
- ✅ **Keep-alive**: Cron Job ile otomatik keep-alive kurulumu şarttır
- 💾 **Backup**: Düzenli backup yapmayı unutmayın

## Sorun Giderme

**Cron Job çalışmıyor mu?**
- Environment variables doğru mu? (özellikle `DATABASE_URL`)
- Logları kontrol edin
- Schedule formatı doğru mu?

**Veriler hala kayboluyor mu?**
- Cron Job'un düzgün çalıştığını kontrol edin
- Schedule çok seyrek olabilir (minimum 30 dakikada bir önerilir)

Detaylı sorun giderme için: **RENDER_DATABASE_KEEP_ALIVE.md** dosyasına bakın.

