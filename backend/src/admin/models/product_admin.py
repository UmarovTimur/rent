import uuid
from pathlib import Path

from markupsafe import Markup
from sqladmin import ModelView
from starlette.datastructures import UploadFile
from starlette.requests import Request
from wtforms import Field
from wtforms.widgets import html_params

from src.clients.database.models.product import Product

MEDIA_PRODUCTS = Path("/media/products")

# Injected once per page via the widget
_GALLERY_SCRIPT = """
<style>
#img-gallery-overlay {
  display:none; position:fixed; inset:0; background:rgba(0,0,0,.7);
  z-index:9999; overflow-y:auto; padding:24px;
}
#img-gallery-overlay.open { display:block; }
#img-gallery-box {
  background:#fff; border-radius:8px; max-width:900px;
  margin:0 auto; padding:20px;
}
#img-gallery-box h3 { margin:0 0 16px; }
#img-gallery-grid {
  display:grid; grid-template-columns:repeat(auto-fill,minmax(120px,1fr)); gap:10px;
}
.gal-item {
  position:relative; cursor:pointer; border:2px solid transparent;
  border-radius:6px; overflow:hidden; aspect-ratio:1;
}
.gal-item:hover { border-color:#3b82f6; }
.gal-item img { width:100%; height:100%; object-fit:cover; display:block; }
.gal-del {
  position:absolute; top:4px; right:4px; background:rgba(220,38,38,.85);
  color:#fff; border:none; border-radius:4px; padding:2px 6px;
  font-size:12px; cursor:pointer; line-height:1.4;
}
#gal-upload-btn {
  display:inline-block; margin-bottom:16px; padding:8px 16px;
  background:#3b82f6; color:#fff; border-radius:6px; cursor:pointer; font-size:14px;
}
#gal-upload-input { display:none; }
#gal-close { float:right; cursor:pointer; font-size:20px; line-height:1; }
</style>

<div id="img-gallery-overlay">
  <div id="img-gallery-box">
    <span id="gal-close" onclick="imgGalleryClose()">&#x2715;</span>
    <h3>Галерея изображений</h3>
    <label id="gal-upload-btn">
      &#8593; Загрузить новое
      <input id="gal-upload-input" type="file" accept="image/*" onchange="galUpload(this)">
    </label>
    <div id="img-gallery-grid"></div>
  </div>
</div>

<script>
(function() {
  if (window._imgGalleryInited) return;
  window._imgGalleryInited = true;

  let _targetFieldId = null;

  window.imgGalleryOpen = function(fieldId) {
    _targetFieldId = fieldId;
    document.getElementById('img-gallery-overlay').classList.add('open');
    galLoadImages();
  };
  window.imgGalleryClose = function() {
    document.getElementById('img-gallery-overlay').classList.remove('open');
  };

  function galLoadImages() {
    fetch('/api/v1/media/products')
      .then(r => r.json())
      .then(urls => {
        const grid = document.getElementById('img-gallery-grid');
        grid.innerHTML = '';
        if (!urls.length) {
          grid.innerHTML = '<p style="color:#888">Нет загруженных изображений</p>';
          return;
        }
        urls.forEach(url => {
          const item = document.createElement('div');
          item.className = 'gal-item';
          item.innerHTML = `<img src="${url}" loading="lazy">
            <button class="gal-del" onclick="galDelete(event,'${url}')">&#x2715;</button>`;
          item.addEventListener('click', function(e) {
            if (e.target.classList.contains('gal-del')) return;
            galSelect(url);
          });
          grid.appendChild(item);
        });
      });
  }

  window.galUpload = function(input) {
    if (!input.files[0]) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    fetch('/api/v1/media/products/upload', { method: 'POST', body: fd })
      .then(r => r.json())
      .then(data => {
        if (data.url) {
          galSelect(data.url);
        }
      });
    input.value = '';
  };

  window.galDelete = function(e, url) {
    e.stopPropagation();
    const filename = url.split('/').pop();
    if (!confirm('Удалить ' + filename + '?')) return;
    fetch('/api/v1/media/products/' + filename, { method: 'DELETE' })
      .then(() => galLoadImages());
  };

  function galSelect(url) {
    if (!_targetFieldId) return;
    const hidden = document.getElementById(_targetFieldId);
    if (hidden) hidden.value = url;
    const preview = document.getElementById(_targetFieldId + '_preview');
    if (preview) { preview.src = url; preview.style.display = 'block'; }
    const clearBtn = document.getElementById(_targetFieldId + '_clear');
    if (clearBtn) clearBtn.style.display = 'inline-block';
    imgGalleryClose();
  }

  window.imgUploadDirect = function(input, fieldId) {
    if (!input.files[0]) return;
    const fd = new FormData();
    fd.append('file', input.files[0]);
    fetch('/api/v1/media/products/upload', { method: 'POST', body: fd })
      .then(r => r.json())
      .then(data => {
        if (data.url) {
          const hidden = document.getElementById(fieldId);
          if (hidden) hidden.value = data.url;
          const preview = document.getElementById(fieldId + '_preview');
          if (preview) { preview.src = data.url; preview.style.display = 'block'; }
          const clearBtn = document.getElementById(fieldId + '_clear');
          if (clearBtn) clearBtn.style.display = 'inline-block';
        }
      });
    input.value = '';
  };

  window.imgClear = function(fieldId) {
    const hidden = document.getElementById(fieldId);
    if (hidden) hidden.value = '';
    const preview = document.getElementById(fieldId + '_preview');
    if (preview) { preview.src = ''; preview.style.display = 'none'; }
    const clearBtn = document.getElementById(fieldId + '_clear');
    if (clearBtn) clearBtn.style.display = 'none';
  };
})();
</script>
"""


class ImagePickerWidget:
    def __call__(self, field, **kwargs):
        fid = field.id
        current = field.data or ""
        has_image = bool(current)

        html = _GALLERY_SCRIPT + f"""
<div style="display:flex;flex-direction:column;gap:8px;align-items:flex-start">
  <img id="{fid}_preview" src="{current}"
       style="max-height:120px;border-radius:6px;{'display:block' if has_image else 'display:none'}">
  <input type="hidden" id="{fid}" name="{field.name}" value="{current}">
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <label style="padding:6px 14px;background:#3b82f6;color:#fff;border-radius:6px;cursor:pointer;font-size:14px">
      &#8593; Загрузить
      <input type="file" accept="image/*" style="display:none"
             onchange="imgUploadDirect(this,'{fid}')">
    </label>
    <button type="button"
            style="padding:6px 14px;background:#6b7280;color:#fff;border-radius:6px;font-size:14px"
            onclick="imgGalleryOpen('{fid}')">
      &#128247; Выбрать из галереи
    </button>
    <button type="button" id="{fid}_clear"
            style="padding:6px 14px;background:#ef4444;color:#fff;border-radius:6px;font-size:14px;{'display:inline-block' if has_image else 'display:none'}"
            onclick="imgClear('{fid}')">
      &#x2715; Убрать
    </button>
  </div>
</div>
"""
        return Markup(html)


class ImagePickerField(Field):
    widget = ImagePickerWidget()

    def process_formdata(self, valuelist):
        self.data = valuelist[0] if valuelist else None

    def _value(self):
        return self.data or ""


class ProductAdmin(ModelView, model=Product):
    column_list = [
        Product.product_id,
        Product.category_id,
        Product.name,
        Product.description,
        Product.price,
        Product.image_url,
    ]
    column_formatters = {
        "image_url": lambda m, a: Markup(
            f'<img src="{m.image_url}" style="height:48px;border-radius:4px;object-fit:cover">'
        ) if m.image_url else "",
    }
    form_overrides = {"image_url": ImagePickerField}
    form_widget_args = {
        "price": {"step": 1, "min": 0},
    }
    name_plural = "Products"

    async def on_model_change(
        self, data: dict, model: Product, is_created: bool, request: Request
    ) -> None:
        value = data.get("image_url")

        # Если пришёл UploadFile (старый путь — на всякий случай)
        if isinstance(value, UploadFile) and value.filename:
            content = await value.read()
            if content:
                MEDIA_PRODUCTS.mkdir(parents=True, exist_ok=True)
                ext = Path(value.filename).suffix.lower() or ".jpg"
                filename = f"{uuid.uuid4().hex}{ext}"
                (MEDIA_PRODUCTS / filename).write_bytes(content)
                data["image_url"] = f"/media/products/{filename}"
                return

        # Пустая строка — не трогаем существующее значение
        if not value:
            data["image_url"] = model.image_url
