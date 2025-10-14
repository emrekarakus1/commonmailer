# ⚠️ ÖNEMLİ: HESABINIZ SİLİNMESİN!

## 🔴 Sorun: Her güncelleme sonrası hesap siliniyor

**Sebep:** PostgreSQL database'i henüz kurulmamış. Sistem hala SQLite kullanıyor ve her deployment'ta container yeniden oluştuğunda veriler gidiyor.

---

## ✅ ÇÖZÜM: PostgreSQL Database Kurulumu (5 Dakika)

### **ADIM 1: Render'da PostgreSQL Oluştur**

1. https://dashboard.render.com adresine git
2. **"New +"** butonuna tıkla
3. **"PostgreSQL"** seç

### **ADIM 2: Database Ayarları**

```
Name: commonportal-db
Database: commonportal
User: (otomatik oluşur)
Region: (Web service ile AYNI region seç - önemli!)
Instance Type: Free
```

4. **"Create Database"** tıkla
5. ⏳ 1-2 dakika bekle

### **ADIM 3: Database URL'ini Kopyala**

1. Database oluştuğunda sayfası açılacak
2. Aşağı kaydır
3. **"Internal Database URL"** başlığını bul
4. Yanındaki **kopyala** butonuna tıkla
   - URL şuna benzer: `postgresql://user:pass@dpg-xxxxx-a.oregon-postgres.render.com/commonportal`

### **ADIM 4: Web Service'e DATABASE_URL Ekle**

1. Sol menüden web service'ine dön (commonportal)
2. **"Environment"** sekmesine tıkla
3. **"Add Environment Variable"** tıkla
4. Şunu ekle:
   ```
   Key: DATABASE_URL
   Value: (kopyaladığın URL'i yapıştır)
   ```
5. **"Save Changes"** tıkla

### **ADIM 5: Deploy Tamamlanmasını Bekle**

- Otomatik yeniden deploy başlayacak
- 2-3 dakika bekle
- ✅ **ARTIK HESABIN KORUNACAK!**

---

## 🎯 Doğrulama

Deploy tamamlandıktan sonra:

1. Siteye git ve yeni hesap oluştur
2. Bir template kaydet
3. Microsoft Graph'a giriş yap
4. **Şimdi başka bir güncelleme yap ve gör:** Hesabın hala orada! ✅

---

## 📊 Mevcut Environment Variables (Kontrol Et)

Render Environment sekmesinde bunlar olmalı:

✅ **DJANGO_SECRET_KEY** - Var
✅ **DJANGO_DEBUG** - Var (False olmalı)
✅ **GRAPH_CLIENT_ID** - Var
✅ **GRAPH_TENANT_ID** - Var
✅ **GRAPH_SCOPES** - Var
✅ **EMAIL_TEMPLATES_PATH** - Var
⚠️ **DATABASE_URL** - **BU EKSİK!** Yukarıdaki adımları takip et!

---

## 💡 Neden PostgreSQL?

### ❌ SQLite (Şu anki durum):
```
Docker Container
├── Django App
└── db.sqlite3 ← HER DEPLOYMENT'TA SİLİNİYOR!
```

### ✅ PostgreSQL (Hedef durum):
```
Docker Container          PostgreSQL Service
├── Django App ─────────→ (Ayrı, kalıcı)
└── (veriler burada yok)  (veriler burada!)
```

---

## 🆘 Sorun mu yaşıyorsun?

### Database bağlanamıyor:
- ✅ **Internal Database URL** kullandığından emin ol (External değil)
- ✅ Database'in "Available" durumda olduğunu kontrol et
- ✅ Region'ların aynı olduğunu kontrol et

### Migration hataları:
```bash
# Render Shell'den çalıştır:
python manage.py migrate --noinput
```

### Hala sorun var:
- DATABASE_URL'i tekrar kopyala/yapıştır
- Yanlış karakter olabilir (boşluk, satır sonu vb.)

---

## ⚡ Hızlı Özet

1. Render → New → PostgreSQL
2. Free plan seç, oluştur
3. Internal Database URL'i kopyala
4. Web Service → Environment → DATABASE_URL ekle
5. Save → Deploy bekle
6. ✅ Artık hesabın korunuyor!

**ŞİMDİ YAP, 5 DAKİKANI AL!** 🚀

