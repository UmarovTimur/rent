// Реальные контакты — поменяйте здесь один раз, подставится во все кнопки и футер.
const CONTACTS = {
  telegram: 'https://t.me/REPLACE_USERNAME', // менеджер в Telegram
  bot: 'https://t.me/camping_rent_uz_bot', // бот для онлайн-бронирования
  phone: '+998 90 000 00 00', // номер для звонка
  instagram: 'https://instagram.com/REPLACE_USERNAME',
};

function applyContacts() {
  document.querySelectorAll('[data-contact="telegram"]').forEach((el) => {
    el.href = CONTACTS.telegram;
    el.target = '_blank';
    el.rel = 'noopener';
  });

  document.querySelectorAll('[data-contact="bot"]').forEach((el) => {
    el.href = CONTACTS.bot;
    el.target = '_blank';
    el.rel = 'noopener';
  });

  document.querySelectorAll('[data-contact="phone"]').forEach((el) => {
    el.href = `tel:${CONTACTS.phone.replace(/[^\d+]/g, '')}`;
    if (!el.textContent.includes('+998')) {
      el.title = CONTACTS.phone;
    }
  });

  document.querySelectorAll('[data-contact="instagram"]').forEach((el) => {
    el.href = CONTACTS.instagram;
    el.target = '_blank';
    el.rel = 'noopener';
  });
}

function setupScrollReveal() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const targets = document.querySelectorAll('.reveal');

  if (prefersReducedMotion || !('IntersectionObserver' in window)) {
    targets.forEach((el) => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
  );

  targets.forEach((el) => observer.observe(el));
}

function setupHeaderScrollState() {
  const header = document.querySelector('.site-header');
  if (!header) return;

  const updateState = () => {
    header.classList.toggle('is-scrolled', window.scrollY > 24);
  };

  updateState();
  window.addEventListener('scroll', updateState, { passive: true });
}

function setFooterYear() {
  const el = document.getElementById('year');
  if (el) el.textContent = new Date().getFullYear();
}

function setupPriceZoom() {
  const img = document.getElementById('price-poster-img');
  if (!img || typeof Viewer === 'undefined') return;

  // eslint-disable-next-line no-new
  new Viewer(img, {
    inline: false,
    navbar: false,
    title: false,
    toolbar: {
      zoomIn: 1,
      zoomOut: 1,
      oneToOne: 1,
      reset: 1,
      prev: 0,
      play: 0,
      next: 0,
      rotateLeft: 0,
      rotateRight: 0,
      flipHorizontal: 0,
      flipVertical: 0,
    },
  });
}

async function copyPriceListLink(button, url) {
  const label = button.querySelector('.price-poster__share-label');
  const originalText = label ? label.textContent : null;

  try {
    await navigator.clipboard.writeText(url);
    if (label) label.textContent = 'Ссылка скопирована';
  } catch {
    window.open(url, '_blank', 'noopener');
    return;
  }

  setTimeout(() => {
    if (label && originalText) label.textContent = originalText;
  }, 2000);
}

function setupPriceShare() {
  const button = document.getElementById('price-poster-share');
  const img = document.getElementById('price-poster-img');
  if (!button || !img) return;

  button.addEventListener('click', async () => {
    const shareData = {
      title: 'Прайс-лист аренды снаряжения',
      text: 'Прайс-лист аренды туристического снаряжения',
      url: img.src,
    };

    try {
      if (navigator.canShare) {
        const response = await fetch(img.src);
        const blob = await response.blob();
        const file = new File([blob], 'price-list.jpg', { type: blob.type || 'image/jpeg' });

        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ ...shareData, files: [file] });
          return;
        }
      }

      if (navigator.share) {
        await navigator.share(shareData);
        return;
      }

      throw new Error('share-unsupported');
    } catch (error) {
      if (error && error.name === 'AbortError') return;
      await copyPriceListLink(button, shareData.url);
    }
  });
}

applyContacts();
setupScrollReveal();
setupHeaderScrollState();
setFooterYear();
setupPriceZoom();
setupPriceShare();
