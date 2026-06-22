// Реальные контакты — поменяйте здесь один раз, подставится во все кнопки и футер.
const CONTACTS = {
  telegram: 'https://t.me/REPLACE_USERNAME', // менеджер в Telegram
  phone: '+998 90 000 00 00', // номер для звонка
  instagram: 'https://instagram.com/REPLACE_USERNAME',
};

function applyContacts() {
  document.querySelectorAll('[data-contact="telegram"]').forEach((el) => {
    el.href = CONTACTS.telegram;
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

applyContacts();
setupScrollReveal();
setFooterYear();
setupPriceZoom();
