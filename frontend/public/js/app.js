// CERBER — fonctions communes à toutes les pages.
// Le jeton de session est dans un cookie HttpOnly : ce script n'y a jamais accès.

/** Appel à l'API. Lève une Error portant le message du serveur en cas d'échec. */
async function api(method, path, body) {
  const options = { method, headers: {}, credentials: 'same-origin' };
  if (body !== undefined) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch('/api' + path, options);
  } catch {
    throw new Error('Serveur injoignable');
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'Erreur ' + response.status);
    error.status = response.status;
    throw error;
  }
  return data;
}

/** Crée un élément DOM. Le texte passe toujours par textContent (pas d'injection HTML). */
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (value === true) node.setAttribute(key, '');
    else if (value !== false && value != null) node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child != null) node.append(child instanceof Node ? child : String(child));
  }
  return node;
}

/** Affiche un message sous un formulaire (élément .msg). */
function say(form, text, kind = 'error') {
  const msg = form.querySelector('.msg');
  msg.textContent = text;
  msg.className = 'msg ' + kind;
}

/**
 * Branche un formulaire : récupère ses champs, désactive le bouton pendant l'appel
 * et affiche l'erreur éventuelle. Le handler peut renvoyer un message de succès.
 */
function onSubmit(form, handler) {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type=submit], button:not([type])');
    const values = Object.fromEntries(new FormData(form));
    if (button) button.disabled = true;
    say(form, '', '');
    try {
      const message = await handler(values, form);
      if (message) say(form, message, 'success');
    } catch (error) {
      if (error.status === 401 && document.body.dataset.auth === 'required') return goLogin();
      say(form, error.message);
    } finally {
      if (button) button.disabled = false;
    }
  });
}

function goLogin() {
  location.href = '/';
}

/**
 * Page demandée avant la connexion (ex. /intranet/). Seuls les chemins locaux
 * sont acceptés, pour empêcher une redirection vers un site externe.
 */
function nextPage() {
  const next = new URLSearchParams(location.search).get('next') || '';
  return /^\/[a-z0-9-]+\/$/.test(next) ? next : null;
}

/** Contrôle ANSSI côté navigateur (le serveur revérifie de toute façon). */
function passwordProblems(password) {
  const rules = [
    [password.length >= 15, 'au moins 15 caractères'],
    [/[a-z]/.test(password), 'une minuscule'],
    [/[A-Z]/.test(password), 'une majuscule'],
    [/[0-9]/.test(password), 'un chiffre'],
    [/[^A-Za-z0-9]/.test(password), 'un caractère spécial'],
  ];
  return rules.filter(([ok]) => !ok).map(([, label]) => label);
}

function checkPassword(password, confirm) {
  const problems = passwordProblems(password);
  if (problems.length) throw new Error('Le mot de passe doit contenir ' + problems.join(', '));
  if (confirm !== undefined && password !== confirm) throw new Error('Les deux mots de passe ne correspondent pas');
}

/** Affiche un QR code TOTP (SVG généré par le serveur) et le secret en clair. */
function showQr(container, setup) {
  container.querySelector('.qr-image').innerHTML = setup.qr_svg;
  container.querySelector('.secret').textContent = setup.secret.match(/.{1,4}/g).join(' ');
  container.hidden = false;
}

/**
 * Pages connectées : charge l'utilisateur, remplit l'en-tête, renouvelle le jeton
 * régulièrement. Renvoie l'utilisateur courant.
 */
async function requireSession({ admin = false } = {}) {
  let me;
  try {
    me = await api('GET', '/me');
  } catch {
    return goLogin();
  }
  if (admin && !me.is_admin) {
    location.href = '/services.html';
    return;
  }
  document.querySelectorAll('[data-admin]').forEach((node) => { node.hidden = !me.is_admin; });
  document.querySelectorAll('header nav a').forEach((a) => {
    if (a.pathname === location.pathname) a.setAttribute('aria-current', 'page');
  });
  document.getElementById('logout')?.addEventListener('click', async () => {
    await api('POST', '/auth/logout').catch(() => {});
    goLogin();
  });
  // Renouvellement du jeton toutes les 45 minutes tant que la page est ouverte
  setInterval(() => api('POST', '/auth/refresh').catch(goLogin), 45 * 60 * 1000);
  document.body.hidden = false;
  return me;
}
