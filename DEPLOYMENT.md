# Render Deployment Talimatları

## PostgreSQL Database Kurulumu

### Adım 1: PostgreSQL Database Oluştur
1. Render Dashboard'a git: https://dashboard.render.com
2. **"New +"** → **"PostgreSQL"** seç
3. Database ayarları:
   - **Name:** `commonportal-db` (veya istediğin isim)
   - **Database:** `commonportal`
   - **User:** `commonportal_user` (otomatik oluşur)
   - **Region:** Aynı region'ı seç (web service ile aynı olmalı)
   - **Plan:** **Free** (0$)
4. **"Create Database"** tıkla
5. Database oluşturulunca **"Internal Database URL"** kopyala

### Adım 2: Web Service'e DATABASE_URL Ekle
1. Web Service'ine git (commonportal)
2. **"Environment"** sekmesine git
3. Yeni environment variable ekle:
   - **Key:** `DATABASE_URL`
   - **Value:** (Kopyaladığın Internal Database URL'i yapıştır)
     - Örnek: `postgresql://commonportal_user:password@dpg-xxxxx.oregon-postgres.render.com/commonportal`
4. **"Save Changes"** tıkla
5. Otomatik deploy başlayacak

### Adım 3: İlk Deployment Sonrası
Deploy tamamlandıktan sonra:
1. Siteye git ve yeni hesap oluştur
2. **Artık her deployment'ta hesabın korunacak!** ✅

---

## Mevcut Environment Variables

Render'da bu değişkenlerin olması gerekiyor:

```env
# Django
DJANGO_SECRET_KEY=d=8Zru85BvHLO9L)dc%O(1278pxnwIeuuocSSQ+RX0=ib^y%i8
DJANGO_DEBUG=False

# Database (Render PostgreSQL'den alınacak)
DATABASE_URL=postgresql://user:password@host/database

# Microsoft Graph API
GRAPH_CLIENT_ID=5178844c-3a2f-445d-93fd-8543183f6757
GRAPH_TENANT_ID=776325fa-1e13-4632-98af-e3e3c8a2297c
GRAPH_SCOPES=Mail.Send
EMAIL_TEMPLATES_PATH=/app/email_templates.json

# Opsiyonel
ALLOWED_HOSTS=your-app.onrender.com
CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com
```

---

## Database Nasıl Çalışıyor?

### Önceki Durum (SQLite):
- ❌ Veritabanı Docker container içindeydi
- ❌ Her deployment'ta container yeniden oluşuyor
- ❌ Tüm veriler (kullanıcılar, templates) siliniyor

### Yeni Durum (PostgreSQL):
- ✅ Veritabanı ayrı bir serviste
- ✅ Container yeniden oluşsa bile veriler korunuyor
- ✅ Kullanıcı hesapları ve template'ler kalıcı

### Local Development:
- Eğer `DATABASE_URL` yoksa otomatik SQLite kullanır
- Local'de PostgreSQL kurmanıza gerek yok

---

## Sorun Giderme

### Database bağlanamıyor hatası:
1. DATABASE_URL doğru kopyalandığından emin ol
2. Internal Database URL kullanıldığından emin ol (External değil)
3. PostgreSQL database'in "Available" durumda olduğunu kontrol et

### Migration hataları:
1. Render logs'a bak: `python manage.py migrate --noinput`
2. Eğer tablo conflict varsa, database'i reset et veya migration'ları düzelt

### İlk süper kullanıcı oluşturma:
Render Shell'den:
```bash
python manage.py createsuperuser
```

---

## Faydalı Komutlar

Render Shell'den çalıştırabileceğin komutlar:

```bash
# Database durumunu kontrol et
python manage.py dbshell

# Migration durumunu gör
python manage.py showmigrations

# Yeni migration oluştur (gerekirse)
python manage.py makemigrations

# Superuser oluştur
python manage.py createsuperuser
```

