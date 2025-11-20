# Kalıcı Veri Depolama Kurulumu

Bu dokümanda uygulamanızın template'lerini ve kullanıcı verilerini kalıcı olarak saklamak için gerekli adımlar açıklanmaktadır.

## Problem

Önceki durumda:
- ❌ Template'ler proje root'unda JSON dosyalarında saklanıyordu
- ❌ OnRender gibi bulut platformlarında her deployment'ta container yeniden oluşuyordu
- ❌ Tüm kullanıcı hesapları ve template'ler siliniyordu
- ❌ Her seferinde aynı maille hesap açmak gerekiyordu

## Çözüm

Yeni sistem:
- ✅ Template'ler persistent storage'da saklanıyor
- ✅ Otomatik backup sistemi
- ✅ Her deployment'ta veriler korunuyor
- ✅ Kullanıcı hesapları ve template'ler kalıcı

## Kurulum Adımları

### 1. OnRender'da Persistent Volume Oluştur

1. Render Dashboard'a git: https://dashboard.render.com
2. **"New +"** → **"Disk"** seç
3. Disk ayarları:
   - **Name:** `commonportal-data`
   - **Mount Path:** `/app/persistent_data`
   - **Size:** 1GB (ücretsiz)
   - **Region:** Web service ile aynı region
4. **"Create Disk"** tıkla

### 2. PostgreSQL Database Oluştur (Önerilen)

1. Render Dashboard'da **"New +"** → **"PostgreSQL"** seç
2. Database ayarları:
   - **Name:** `commonportal-db`
   - **Database:** `commonportal`
   - **Region:** Web service ile aynı region
   - **Plan:** **Free** (0$)
3. **"Create Database"** tıkla
4. **"Internal Database URL"** kopyala

### 3. Environment Variables Ekle

Web Service'inizde bu environment variables'ları ekleyin:

```env
# Database
DATABASE_URL=postgresql://user:password@host/database

# Persistent Storage
DATA_STORAGE_PATH=/app/persistent_data
EMAIL_TEMPLATES_PATH=/app/persistent_data/email_templates.json
USER_TEMPLATES_PATH=/app/persistent_data/user_templates

# Diğer ayarlar (mevcut)
DJANGO_SECRET_KEY=your-secret-key
GRAPH_CLIENT_ID=your-client-id
GRAPH_TENANT_ID=your-tenant-id
```

### 4. Deployment

Environment variables'ları ekledikten sonra:
1. **"Save Changes"** tıkla
2. Otomatik deploy başlayacak
3. Deploy tamamlandıktan sonra siteye git
4. Yeni hesap oluştur veya mevcut hesabınla giriş yap

## Yerel Geliştirme

Yerel geliştirme için özel bir şey yapmanıza gerek yok:

- Eğer `DATABASE_URL` yoksa otomatik SQLite kullanır
- Template'ler local `persistent_data` klasöründe saklanır
- Tüm özellikler yerel ortamda da çalışır

## Backup Sistemi

### Otomatik Backup
- Her template kaydetme/silme işleminde otomatik backup oluşturulur
- Son 10 backup korunur, eskiler otomatik silinir

### Manuel Backup
```bash
# Tüm kullanıcılar için backup
python manage.py backup_user_data

# Belirli kullanıcı için backup
python manage.py backup_user_data --user-id 1

# Eski backup'ları temizle
python manage.py backup_user_data --cleanup --keep-count 5
```

### Backup'dan Restore
```python
# Django shell'den
from automation.services.backup import backup_service
success = backup_service.restore_backup('/path/to/backup.json', user_id=1)
```

## Migration (Mevcut Veriler için)

Eğer zaten template'leriniz varsa:

```bash
# Dry run (ne yapacağını göster)
python manage.py migrate_to_persistent_storage --dry-run

# Gerçek migration
python manage.py migrate_to_persistent_storage
```

## Sorun Giderme

### Template'ler görünmüyor
1. Persistent volume'un mount edildiğini kontrol edin
2. Environment variables'ların doğru olduğunu kontrol edin
3. Migration'ı tekrar çalıştırın

### Backup'lar oluşturulmuyor
1. Persistent storage yazma izinlerini kontrol edin
2. Log'ları kontrol edin: `python manage.py shell -c "import logging; logging.basicConfig(level=logging.DEBUG)"`

### Database bağlantı sorunu
1. DATABASE_URL'in doğru olduğunu kontrol edin
2. PostgreSQL database'in "Available" durumda olduğunu kontrol edin
3. Internal Database URL kullandığınızdan emin olun

## Faydalı Komutlar

```bash
# Template'leri listele
python manage.py shell -c "from automation.services.templates import TemplateService; ts = TemplateService(user_id=1); print(ts.get_templates())"

# Backup'ları listele
python manage.py shell -c "from automation.services.backup import backup_service; print(backup_service.list_backups())"

# Persistent storage durumunu kontrol et
python manage.py shell -c "from django.conf import settings; import os; print('Storage path:', settings.DATA_STORAGE_PATH); print('Exists:', os.path.exists(settings.DATA_STORAGE_PATH))"
```

## Sonuç

Bu kurulum ile:
- ✅ Kullanıcı hesaplarınız kalıcı olacak
- ✅ Template'leriniz kaybolmayacak
- ✅ Her deployment'ta veriler korunacak
- ✅ Otomatik backup sistemi ile güvenlik artacak
- ✅ Artık aynı maille tekrar hesap açmak zorunda kalmayacaksınız

Herhangi bir sorun yaşarsanız, log'ları kontrol edin veya backup'lardan restore yapın.
