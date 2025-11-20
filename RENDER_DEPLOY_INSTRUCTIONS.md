# Render Deploy Talimatları

## Problem
GitHub'a push yapıldı ama Render'da otomatik deploy olmadı.

## Çözüm: Manuel Deploy

### Adım 1: Render Dashboard'a Git
1. https://dashboard.render.com adresine git
2. Login ol
3. **commonmailer** servisini bul ve tıkla

### Adım 2: Manuel Deploy Yap
1. Servis sayfasında sağ üstte **"Manual Deploy"** butonunu bul
2. **"Deploy latest commit"** seçeneğini tıkla
3. Deploy işlemi başlayacak (2-5 dakika sürebilir)

### Adım 3: Deploy Durumunu Kontrol Et
1. **"Events"** veya **"Logs"** sekmesine git
2. Deploy işleminin tamamlanmasını bekle
3. Yeşil "Live" durumunu görünce deploy başarılı demektir

## Otomatik Deploy'u Aktif Et (Gelecek için)

### Adım 1: Auto-Deploy Ayarlarını Kontrol Et
1. Servis sayfasında **"Settings"** sekmesine git
2. **"Auto-Deploy"** bölümünü bul
3. **"Auto-Deploy"** seçeneğinin **"Yes"** olduğundan emin ol
4. **Branch** ayarının **"main"** olduğundan emin ol

### Adım 2: Webhook Kontrolü
1. **"Settings"** → **"Service Details"** bölümüne git
2. **"GitHub Repository"** bağlantısının doğru olduğundan emin ol
3. Eğer bağlantı yoksa, **"Connect GitHub"** butonuna tıkla

## Deploy Sonrası Kontrol

Deploy tamamlandıktan sonra:
1. https://commonmailer.onrender.com adresine git
2. Yeni özelliklerin çalıştığını kontrol et:
   - ✅ Signup formu sadece email ve password istiyor mu?
   - ✅ Dry run çalışıyor mu?
   - ✅ Template whitespace korunuyor mu?
   - ✅ Logout sonrası Microsoft cache temizleniyor mu?

## Sorun Giderme

### Deploy başarısız olursa:
1. **"Logs"** sekmesine git
2. Hata mesajlarını kontrol et
3. Genellikle şu hatalar olabilir:
   - Migration hataları → Render Shell'den `python manage.py migrate` çalıştır
   - Environment variable eksik → Settings'ten kontrol et
   - Build hatası → requirements.txt'i kontrol et

### Deploy çok uzun sürerse:
- Render'ın free plan'ında deploy 5-10 dakika sürebilir
- Sabırla bekle, deploy tamamlanana kadar sayfayı yenileme

## Hızlı Komutlar

Render Shell'den (Render Dashboard → Shell):
```bash
# Son commit'i kontrol et
git log -1

# Migration durumunu kontrol et
python manage.py showmigrations

# Gerekirse migration yap
python manage.py migrate
```

