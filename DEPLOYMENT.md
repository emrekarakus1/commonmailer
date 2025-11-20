# Render Deployment Talimatları

## Kalıcı Veri Depolama Kurulumu

### Adım 1: PostgreSQL Database Oluştur (Önerilen)
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

### Adım 2: Persistent Volume Kurulumu (Template'ler için)
1. Render Dashboard'da **"New +"** → **"Disk"** seç
2. Disk ayarları:
   - **Name:** `commonportal-data`
   - **Mount Path:** `/app/persistent_data`
   - **Size:** 1GB (ücretsiz)
   - **Region:** Web service ile aynı region
3. **"Create Disk"** tıkla
4. Disk oluşturulunca **Mount Path**'i not et

### Adım 3: Web Service'e Environment Variables Ekle
1. Web Service'ine git (commonportal)
2. **"Environment"** sekmesine git
3. Bu environment variables'ları ekle:

**Database için:**
   - **Key:** `DATABASE_URL`
   - **Value:** (PostgreSQL Internal Database URL'i yapıştır)

**Persistent Storage için:**
   - **Key:** `DATA_STORAGE_PATH`
   - **Value:** `/app/persistent_data`
   - **Key:** `EMAIL_TEMPLATES_PATH`
   - **Value:** `/app/persistent_data/email_templates.json`
   - **Key:** `USER_TEMPLATES_PATH`
   - **Value:** `/app/persistent_data/user_templates`

4. **"Save Changes"** tıkla
5. Otomatik deploy başlayacak

### Adım 4: İlk Deployment Sonrası
Deploy tamamlandıktan sonra:
1. Siteye git ve yeni hesap oluştur
2. **Artık her deployment'ta hesabın ve template'lerin korunacak!** ✅

---

## Mevcut Environment Variables

Render'da bu değişkenlerin olması gerekiyor:

```env
# Django
DJANGO_SECRET_KEY=d=8Zru85BvHLO9L)dc%O(1278pxnwIeuuocSSQ+RX0=ib^y%i8
DJANGO_DEBUG=False

# Database (Render PostgreSQL'den alınacak)
DATABASE_URL=postgresql://user:password@host/database

# Persistent Storage (Render Disk'ten alınacak)
DATA_STORAGE_PATH=/app/persistent_data
EMAIL_TEMPLATES_PATH=/app/persistent_data/email_templates.json
USER_TEMPLATES_PATH=/app/persistent_data/user_templates

# Microsoft Graph API
GRAPH_CLIENT_ID=5178844c-3a2f-445d-93fd-8543183f6757
GRAPH_TENANT_ID=776325fa-1e13-4632-98af-e3e3c8a2297c
GRAPH_SCOPES=Mail.Send

# Opsiyonel
ALLOWED_HOSTS=your-app.onrender.com
CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com
```

---

## Veri Depolama Nasıl Çalışıyor?

### Önceki Durum (SQLite + JSON dosyaları):
- ❌ Veritabanı Docker container içindeydi
- ❌ Template'ler proje root'unda JSON dosyalarında
- ❌ Her deployment'ta container yeniden oluşuyor
- ❌ Tüm veriler (kullanıcılar, templates) siliniyor

### Yeni Durum (PostgreSQL + Persistent Volume):
- ✅ Veritabanı ayrı bir serviste (PostgreSQL)
- ✅ Template'ler persistent disk'te saklanıyor
- ✅ Container yeniden oluşsa bile veriler korunuyor
- ✅ Kullanıcı hesapları ve template'ler kalıcı
- ✅ Otomatik backup sistemi

### Local Development:
- Eğer `DATABASE_URL` yoksa otomatik SQLite kullanır
- Template'ler local `persistent_data` klasöründe saklanır
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

# Template'leri persistent storage'a migrate et
python manage.py migrate_to_persistent_storage

# Kullanıcı verilerini backup'la
python manage.py backup_user_data

# Belirli bir kullanıcının backup'ını oluştur
python manage.py backup_user_data --user-id 1

# Eski backup'ları temizle
python manage.py backup_user_data --cleanup --keep-count 5
```

---

## Backup ve Restore

### Otomatik Backup
- Her template kaydetme işleminde otomatik backup oluşturulur
- Eski backup'lar otomatik temizlenir (son 10 backup korunur)

### Manuel Backup
```bash
# Tüm kullanıcılar için backup
python manage.py backup_user_data

# Belirli kullanıcı için backup
python manage.py backup_user_data --user-id 1
```

### Backup'ları Listele
```python
# Django shell'den
from automation.services.backup import backup_service
backups = backup_service.list_backups(user_id=1)
```

### Backup'dan Restore
```python
# Django shell'den
from automation.services.backup import backup_service
success = backup_service.restore_backup('/path/to/backup.json', user_id=1)
```

