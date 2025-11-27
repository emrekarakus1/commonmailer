# Render Veritabanı Silinme Sorunu ve Çözümü

> 📚 **Hızlı Başlangıç İçin**: Detaylı adım adım rehber için **CRON_JOB_HIZLI_BASLANGIC.md** veya **RENDER_CRON_JOB_ADIM_ADIM.md** dosyalarına bakın.
> 
> **Hızlı Sorular:**
> - DATABASE_URL nerede? → PostgreSQL veritabanı → "Connections" sekmesi → "Internal Database URL"
> - Environment variables nereye? → Cron Job oluşturulduktan sonra → "Environment" sekmesi
> - Command ne yazmalıyım? → `python manage.py keep_database_alive`

## Problem

Render'ın **ücretsiz PostgreSQL veritabanı** planında, uygulama belirli bir süre kullanılmadığında veritabanı tamamen silinebiliyor. Bu durum şu sebeplerden kaynaklanır:

1. **90 Gün İnaktivite Kuralı**: Render'ın free PostgreSQL planında, 90 gün boyunca hiç kullanılmayan veritabanları otomatik olarak silinebilir.

2. **Otomatik Spin-Down**: Ücretsiz planlarda, veritabanı inaktif kaldığında spin-down (kapanma) yapar ve uzun süre kapalı kalırsa silinebilir.

3. **Veri Kaybı**: Veritabanı silindiğinde içindeki tüm veriler (kullanıcılar, şablonlar, vb.) kalıcı olarak kaybolur.

## Çözüm Seçenekleri

### ✅ Çözüm 1: Otomatik Keep-Alive (Önerilen - Ücretsiz)

Veritabanını aktif tutmak için periyodik olarak basit bir sorgu çalıştırın. Bu, veritabanının "aktif" olarak işaretlenmesini sağlar.

#### Adım 1: DATABASE_URL'i Bul

**DATABASE_URL'i nereden bulacaksınız?**

**Yöntem 1: PostgreSQL Veritabanı Sayfasından (Önerilen)**

1. Render Dashboard'da **PostgreSQL veritabanınızı** bulun (örn: `commonportal-db`)
2. Veritabanı sayfasına tıklayın
3. Üst menüde **"Connections"** sekmesine tıklayın
4. **"Internal Database URL"** değerini kopyalayın
   - Format: `postgresql://kullanici:şifre@host:5432/veritabani_adi`
   - ⚠️ **ÖNEMLİ**: "External Database URL" değil, **"Internal Database URL"** kopyalayın!

**Yöntem 2: Web Servisinden**

1. Render Dashboard'da **Web servisinizi** bulun (örn: `commonmailer` veya `commonportal`)
2. Web servis sayfasına tıklayın
3. Üst menüde **"Environment"** sekmesine tıklayın
4. **"Environment Variables"** listesinde `DATABASE_URL` değerini bulun
5. Değeri kopyalayın

---

#### Adım 2: Render Cron Job Oluştur

1. **Render Dashboard'a Git**
   - https://dashboard.render.com adresine git
   - Login ol

2. **Yeni Cron Job Oluştur**
   - Sol üstteki **"New +"** butonuna tıklayın
   - Açılan menüden **"Cron Job"** seçeneğini seçin

3. **Temel Ayarları Doldur**
   - **Name**: `keep-database-alive` (veya istediğin isim)
   - **Schedule**: `*/30 * * * *` (Her 30 dakikada bir)
     - Daha sık tutmak için: `*/15 * * * *` (15 dakika)
     - Daha seyrek için: `0 * * * *` (Her saat başı)
   - **Command**: `python manage.py keep_database_alive`
     - ⚠️ **ÖNEMLİ**: Command, projenin root dizininde (manage.py'nin olduğu yer) çalışır
     - Bu yüzden sadece `python manage.py keep_database_alive` yazmanız yeterli
     - ❌ `cd /app && python manage.py keep_database_alive` gibi bir şey yazmanıza gerek yok
     - ✅ Render otomatik olarak doğru dizinde çalıştırır
   - **Service**: Açılır menüden web servisinizi seçin (örn: `commonmailer`)
   - **Region**: Web servisiyle aynı region'ı seçin
   - **Plan**: **Free** (ücretsiz)

4. **"Create Cron Job"** butonuna tıklayın
   - Cron Job oluşturulacak ve yeni sayfaya yönlendirileceksiniz

---

#### Adım 3: Environment Variables Ekle

**⚠️ ÖNEMLİ**: Environment Variables'ları **Cron Job oluşturulduktan SONRA** ekliyorsunuz!

1. **Cron Job Sayfasına Gidin**
   - Cron Job oluşturulduktan sonra otomatik olarak Cron Job sayfasına yönlendirileceksiniz
   - Veya Dashboard'dan Cron Job'unuzu bulup tıklayın

2. **Environment Sekmesine Gidin**
   - Cron Job sayfasının **üst menüsünde** (Overview, Environment, Logs, Settings, vb.) **"Environment"** sekmesine tıklayın

3. **Environment Variables Ekleme**
   - Sayfada **"Environment Variables"** bölümünü bulun
   - **"Add Environment Variable"** veya **"+"** butonuna tıklayın
   
4. **DATABASE_URL Ekleyin**
   - **Key**: `DATABASE_URL`
   - **Value**: Adım 1'de kopyaladığınız Internal Database URL'i yapıştırın
   - **"Save"** butonuna tıklayın

5. **Diğer Gerekli Değişkenleri Ekleyin (Opsiyonel)**
   - Eğer Django başka environment variables kullanıyorsa, onları da ekleyin:
     - `DJANGO_SECRET_KEY` (varsa)
     - Diğer gerekli değişkenler
   - ⚠️ **Not**: `DATABASE_URL` en önemlisi, diğerleri genelde opsiyonel

**Ekran Görüntüsü Rehberi**:
```
Cron Job Sayfası:
┌─────────────────────────────────────┐
│ Overview | Environment | Logs | ... │ ← Burada "Environment" sekmesine tıkla
├─────────────────────────────────────┤
│                                     │
│ Environment Variables               │
│ ┌─────────────────────────────────┐ │
│ │ Key          Value              │ │
│ ├─────────────────────────────────┤ │
│ │ DATABASE_URL postgresql://...   │ │ ← Buraya ekle
│ └─────────────────────────────────┘ │
│                                     │
│ [+ Add Environment Variable]        │ ← Bu butona tıkla
└─────────────────────────────────────┘
```

#### Adım 4: Test Et

1. Cron Job sayfasında **"Manual Trigger"** butonuna tıklayın
   - Bu buton sayfanın sağ üst köşesinde veya "Overview" sekmesinde olabilir
2. **"Logs"** sekmesine gidin
   - Üst menüden "Logs" sekmesine tıklayın
3. Komutun başarıyla çalıştığını kontrol edin
   - Şu mesajı görmelisiniz: `✓ Database connection is alive. Query result: (1,)`
   - Veya: `ok`
   
**⚠️ Eğer hata görüyorsanız:**
- `DATABASE_URL` environment variable'ının doğru eklendiğinden emin olun
- Logları tekrar kontrol edin
- "Manual Trigger" ile tekrar deneyin

#### Adım 5: Doğrulama

1. Birkaç saat veya bir gün bekle
2. Uygulamanıza girin ve verilerin hala mevcut olduğunu kontrol edin
3. ✅ **BAŞARILI!** Veritabanı artık aktif kalacak

---

### ✅ Çözüm 2: Harici Keep-Alive Servisi (Alternatif)

Render Cron Job yerine, harici bir servis (örn: UptimeRobot, cron-job.org) kullanarak health check endpoint'ini periyodik olarak çağırabilirsiniz.

#### Adım 1: Health Check Endpoint'ini Kullan

Uygulamanızda zaten bir health check endpoint'i var: `/healthz/`

Bu endpoint veritabanı bağlantısını test eder ve veritabanını aktif tutar.

#### Adım 2: Harici Servis Kurulumu

1. **UptimeRobot** (https://uptimerobot.com) veya **cron-job.org** gibi bir servis kullanın
2. Yeni bir monitoring/health check oluşturun:
   - **URL**: `https://your-app.onrender.com/healthz/`
   - **Interval**: 15-30 dakika
3. Bu servis periyodik olarak endpoint'inizi çağıracak ve veritabanı aktif kalacak

---

### ✅ Çözüm 3: Paid Plan'e Geçiş (En Güvenilir)

Render'ın **ücretli PostgreSQL planları** (Starter: $7/ay) veritabanını silmez ve otomatik yedekleme sunar.

**Avantajlar:**
- ✅ Veritabanı asla silinmez
- ✅ Otomatik günlük yedeklemeler
- ✅ Daha fazla depolama alanı
- ✅ 7/24 destek

**Plan Değiştirme:**
1. Render Dashboard'da PostgreSQL veritabanınızı bulun
2. **"Settings"** → **"Plan"** bölümüne gidin
3. **"Starter"** veya daha yüksek bir plan seçin

---

### ✅ Çözüm 4: Düzenli Manuel Backup (Güvenlik Önlemi)

Keep-alive çalışsa bile, verilerinizi düzenli olarak yedekleyin.

#### Otomatik Backup Command

Zaten mevcut bir backup komutu var:

```bash
# Tüm kullanıcılar için backup
python manage.py backup_user_data

# Belirli kullanıcı için backup
python manage.py backup_user_data --user-id 1

# Eski backup'ları temizle
python manage.py backup_user_data --cleanup --keep-count 10
```

#### Backup'ları Render Disk'e Kaydet

Backup dosyalarınızı Render Persistent Disk'e kaydedebilirsiniz. Böylece container yenilense bile backup'lar korunur.

---

## Cron Job Schedule Örnekleri

Cron Job schedule'ı için farklı seçenekler:

| Açıklama | Schedule | Açıklama |
|----------|----------|----------|
| Her 15 dakika | `*/15 * * * *` | Çok sık (gerekirse) |
| Her 30 dakika | `*/30 * * * *` | **Önerilen** |
| Her saat başı | `0 * * * *` | Normal kullanım için yeterli |
| Her 6 saatte bir | `0 */6 * * *` | Minimum (riskli) |
| Günlük | `0 0 * * *` | Yetersiz - veritabanı silinebilir |

**Öneri**: `*/30 * * * *` (her 30 dakikada bir) - Veritabanını aktif tutar ama çok fazla kaynak tüketmez.

---

## Sorun Giderme

### Cron Job Çalışmıyor

**Kontrol Listesi:**
1. Cron Job'un durumu "Active" olmalı
2. Environment variables (özellikle `DATABASE_URL`) doğru ayarlanmış olmalı
3. Loglarda hata mesajı var mı kontrol et
4. Schedule formatı doğru mu? (crontab formatı: `minute hour day month weekday`)

### "Database connection failed" Hatası

**Çözüm:**
1. `DATABASE_URL` environment variable'ının doğru olduğundan emin ol
2. Internal Database URL kullanıldığından emin ol (External değil)
3. PostgreSQL veritabanının durumu "Available" olmalı

### Veriler Hala Kayboluyor

**Kontrol Et:**
1. Cron Job düzgün çalışıyor mu? Logları kontrol et
2. Cron Job'un schedule'ı çok seyrek mi? (ör: günlük yetersiz)
3. Veritabanı planı free mi? 90 gün inaktivite kuralı hala geçerli

---

## Özet

✅ **En İyi Çözüm**: Render Cron Job ile otomatik keep-alive (Çözüm 1)
✅ **Alternatif**: Harici servis ile health check (Çözüm 2)
✅ **En Güvenilir**: Paid plan'e geçiş (Çözüm 3)
✅ **Güvenlik**: Düzenli backup (Çözüm 4)

**Önerilen Kombinasyon:**
- Render Cron Job (her 30 dakikada bir)
- Düzenli backup'lar
- (İsteğe bağlı) Paid plan'e geçiş

Bu kombinasyon ile veritabanınızın silinmesi riski minimuma iner! 🎉

