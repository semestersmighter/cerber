/** Chemin pour un service local (/intranet), nom d'hôte pour un site externe. */
function where(url) {
  const u = new URL(url, location.origin);
  return u.origin === location.origin ? u.pathname.replace(/\/$/, '') : u.host;
}

(async () => {
  const me = await requireSession();
  if (!me) return;
  document.querySelector('main > p').textContent =
    'Rôles : ' + (me.roles.join(', ') || 'aucun') + '. Voici les services auxquels vous avez accès.';

  const services = await api('GET', '/me/resources');
  const list = document.getElementById('services');
  for (const s of services) {
    list.append(el('li', {}, el('a', { href: s.url, rel: 'noopener' }, el('span', {}, s.name), el('small', {}, where(s.url)))));
  }
  document.getElementById('empty').hidden = services.length > 0;
})();
