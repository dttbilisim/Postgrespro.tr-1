# Blog Scraping Script

Bu script, postgrespro.com/blog'daki tüm blog yazılarını otomatik olarak çeker ve JSON formatında kaydeder.

## Kurulum

1. Python 3.8+ yüklü olduğundan emin olun
2. Gerekli paketleri yükleyin:

```bash
pip install -r requirements.txt
```

## Kullanım

Script'i çalıştırmak için:

```bash
python scrape_blog.py
```

Script şunları yapar:
- postgrespro.com/blog'daki tüm blog yazılarını bulur
- Her yazının içeriğini çeker
- Görselleri indirir
- JSON dosyalarını `wwwroot/content/blog/` klasörüne kaydeder
- Görselleri `wwwroot/blog/{slug}/` klasörüne kaydeder

## Çıktı Formatı

Her blog yazısı için bir JSON dosyası oluşturulur:
- Dosya adı: `{slug}.json`
- Konum: `wwwroot/content/blog/`

JSON formatı:
```json
{
  "title": "Post Title",
  "titleTr": "Yazı Başlığı",
  "slug": "post-slug",
  "date": "2024-01-01T00:00:00",
  "author": "Author Name",
  "category": "PostgreSQL",
  "categoryTr": "PostgreSQL",
  "tags": ["tag1", "tag2"],
  "tagsTr": ["etiket1", "etiket2"],
  "sourceUrl": "https://postgrespro.com/blog/...",
  "canonicalUrl": "https://postgrespro.com/blog/...",
  "excerpt": "Short excerpt...",
  "excerptTr": "Kısa özet...",
  "content": "<html>...</html>",
  "contentTr": "<html>...</html>",
  "readingTime": 5,
  "heroImage": "/blog/slug/image.jpg",
  "images": ["/blog/slug/image1.jpg"],
  "published": true
}
```

## Notlar

- Script, sunucuya saygılı olmak için her istek arasında 2 saniye bekler
- Görseller otomatik olarak indirilir ve yerel yollara dönüştürülür
- HTML içeriği temizlenir (reklamlar, abonelik kutuları vb. kaldırılır)
- Türkçe karakterler slug'larda düzgün işlenir

