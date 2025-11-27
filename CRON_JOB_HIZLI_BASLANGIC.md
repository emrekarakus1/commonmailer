# Cron Job Hızlı Başlangıç - Türkçe

## 🎯 Sorularınızın Cevapları

### 1. DATABASE_URL'i Nerede Bulacağım?

**En Kolay Yol:**

1. Render Dashboard'da (https://dashboard.render.com) giriş yapın
2. Sol menüden **PostgreSQL veritabanınızı** bulun ve **tıklayın**
3. Sayfanın üstünde **"Connections"** sekmesine **tıklayın**
4. **"Internal Database URL"** yazısının altındaki uzun metni **kopyalayın**
   - Format: `postgresql://kullanici:şifre@hostname:5432/veritabani`
   - ⚠️ "External Database URL" değil, **"Internal Database URL"** kopyalayın!

**Alternatif Yol (Web Servisinden):**

1. Dashboard'da **web servisinizi** bulun ve tıklayın
2. **"Environment"** sekmesine tıklayın
3. `DATABASE_URL` değerini bulun ve kopyalayın

---

### 2. Environment Variables Nereye Yazılacak?

**ÖNEMLİ**: Önce Cron Job'u oluşturmanız gerekiyor!

#### Adımlar:

1. ✅ **Önce Cron Job'u oluşturun** ("New +" → "Cron Job" → "Create Cron Job")

2. ✅ **Cron Job sayfasına gidin** (otomatik yönlendirileceksiniz)

3. ✅ **Üst menüde "Environment" sekmesine tıklayın**
   ```
   [Overview] [Environment] [Logs] [Settings]
                    ↑
              Buraya tıkla!
   ```

4. ✅ **"+ Add Environment Variable" butonuna tıklayın**

5. ✅ **Değerleri girin:**
   - Key: `DATABASE_URL`
   - Value: Kopyaladığınız Internal Database URL'i yapıştırın

6. ✅ **"Save" butonuna tıklayın**

**Not**: Environment sekmesi sadece Cron Job oluşturulduktan sonra görünür!

---

### 3. Command Çalışma Dizini

**Cevap**: Render otomatik olarak doğru dizinde çalıştırır.

**Command alanına sadece şunu yazın:**
```
python manage.py keep_database_alive
```

**Yazmayın:**
- ❌ `cd /app && python manage.py keep_database_alive`
- ❌ `python /app/manage.py keep_database_alive`

**Neden?**
- Render zaten `manage.py` dosyasının olduğu dizinde çalıştırır
- Ekstra `cd` komutuna gerek yok

---

## 📝 Hızlı Kurulum (3 Adım)

### 1️⃣ DATABASE_URL'i Kopyala
- PostgreSQL veritabanı → "Connections" → "Internal Database URL" kopyala

### 2️⃣ Cron Job Oluştur
- Dashboard → "New +" → "Cron Job"
- Name: `keep-database-alive`
- Schedule: `*/30 * * * *`
- Command: `python manage.py keep_database_alive`
- Service: Web servisinizi seçin
- "Create Cron Job" tıklayın

### 3️⃣ Environment Variable Ekle
- Cron Job sayfası → "Environment" sekmesi
- "+ Add Environment Variable"
- Key: `DATABASE_URL`
- Value: Kopyaladığınız URL'i yapıştırın
- "Save" tıklayın

---

## ✅ Test Et

1. Cron Job sayfasında **"Manual Trigger"** butonuna tıklayın
2. **"Logs"** sekmesine gidin
3. Şu mesajı görmelisiniz: `✓ Database connection is alive`

---

## ❓ Sorun mu Var?

**Environment sekmesini göremiyorum:**
- Cron Job'u önce oluşturmanız gerekiyor

**Command çalışmıyor:**
- Sadece `python manage.py keep_database_alive` yazın, başka bir şey eklemeyin

**DATABASE_URL bulamıyorum:**
- PostgreSQL veritabanı sayfası → "Connections" sekmesi → "Internal Database URL"

---

## 📚 Detaylı Rehberler

Daha fazla detay için:
- **RENDER_CRON_JOB_ADIM_ADIM.md** - Çok detaylı adım adım rehber
- **RENDER_DATABASE_KEEP_ALIVE.md** - Tam dokümantasyon

---

**Hazır! Artık veritabanınız silinmeyecek! 🎉**

