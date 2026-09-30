(async () => {
  const me = await requireSession({ admin: true });
  if (!me) return;

  const roles = await api('GET', '/admin/roles');
  const roleName = Object.fromEntries(roles.map((r) => [r.id, r.name]));

  /** Cases à cocher des rôles ; `checked` = ids déjà sélectionnés. */
  function roleChecks(name, checked = []) {
    return roles.map((r) => el('label', {},
      el('input', { type: 'checkbox', name, value: r.id, checked: checked.includes(r.id) }), r.name));
  }
  const checkedIds = (root) => [...root.querySelectorAll('input[type=checkbox]:checked')].map((i) => Number(i.value));

  document.querySelectorAll('[data-roles]').forEach((box) => box.append(...roleChecks(box.dataset.roles)));

  function flash(id, text, kind = 'success') {
    const msg = document.getElementById(id);
    msg.textContent = text;
    msg.className = 'msg ' + kind;
  }

  /** Bouton d'action de tableau : confirmation, appel API, rechargement. */
  function action(label, msgId, { confirmText, danger, run, reload }) {
    return el('button', {
      type: 'button', class: 'ghost small' + (danger ? ' danger' : ''),
      onclick: async (event) => {
        if (confirmText && !confirm(confirmText)) return;
        event.target.disabled = true;
        try {
          flash(msgId, (await run()).message);
          await reload();
        } catch (error) {
          flash(msgId, error.message, 'error');
          event.target.disabled = false;
        }
      },
    }, label);
  }

  // ---------- Comptes ----------

  async function loadUsers() {
    const users = await api('GET', '/admin/users');
    document.getElementById('users').replaceChildren(...users.map((u) => el('tr', {},
      el('td', {}, u.nif),
      el('td', {}, u.email),
      el('td', {}, u.roles.join(', ')),
      el('td', {},
        u.locked ? el('span', { class: 'tag err' }, 'verrouillé') : el('span', { class: 'tag ok' }, 'actif'), ' ',
        u.totp_enabled ? '' : el('span', { class: 'tag' }, 'TOTP à configurer')),
      el('td', { class: 'actions' },
        u.locked ? action('Déverrouiller', 'users-msg', {
          run: () => api('POST', `/admin/users/${u.nif}/unlock`), reload: loadUsers }) : null,
        u.totp_enabled ? action('Réinit. TOTP', 'users-msg', {
          confirmText: `Réinitialiser l'application TOTP de ${u.nif} ? Il devra en enregistrer une nouvelle à sa prochaine connexion.`,
          run: () => api('POST', `/admin/users/${u.nif}/reset-totp`), reload: loadUsers }) : null,
        u.nif === me.nif ? null : action('Supprimer', 'users-msg', {
          danger: true, confirmText: `Supprimer définitivement le compte ${u.nif} ?`,
          run: () => api('DELETE', `/admin/users/${u.nif}`), reload: loadUsers })),
    )));
  }

  onSubmit(document.getElementById('user-form'), async ({ nif, email, address, password }, form) => {
    checkPassword(password);
    const role_ids = checkedIds(form);
    if (!role_ids.length) throw new Error('Choisissez au moins un rôle');
    await api('POST', '/admin/users', { nif, email, address, password, role_ids });
    form.reset();
    await loadUsers();
    return `Compte ${nif} créé.`;
  });

  // ---------- Ressources ----------

  async function loadResources() {
    const resources = await api('GET', '/admin/resources');
    document.getElementById('resources').replaceChildren(...resources.map((r) => {
      const checks = el('div', { class: 'checks' }, roleChecks('r' + r.id, r.role_ids));
      return el('tr', {},
        el('td', {}, el('a', { href: r.url, rel: 'noopener' }, r.name)),
        el('td', {}, r.slug),
        el('td', {}, checks),
        el('td', { class: 'actions' },
          action('Enregistrer', 'resources-msg', {
            run: () => api('PUT', `/admin/resources/${r.id}/roles`, { role_ids: checkedIds(checks) }),
            reload: loadResources }),
          action('Supprimer', 'resources-msg', {
            danger: true, confirmText: `Supprimer la ressource « ${r.name} » ?`,
            run: () => api('DELETE', `/admin/resources/${r.id}`), reload: loadResources })));
    }));
  }

  onSubmit(document.getElementById('resource-form'), async ({ name, slug, url }, form) => {
    await api('POST', '/admin/resources', { name, slug, url, role_ids: checkedIds(form) });
    form.reset();
    await loadResources();
    return `Ressource « ${name} » ajoutée.`;
  });

  // ---------- Journal ----------

  const eventsForm = document.getElementById('events-form');
  const dateFormat = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'medium' });

  async function loadEvents(filters = {}) {
    const params = new URLSearchParams(Object.entries(filters).filter(([, v]) => v !== ''));
    const data = await api('GET', '/admin/events?' + params);
    const typeSelect = eventsForm.type;
    if (typeSelect.options.length === 1) {
      typeSelect.append(...data.types.map((t) => el('option', { value: t }, t)));
    }
    document.getElementById('events').replaceChildren(...data.events.map((e) => el('tr', {},
      el('td', {}, dateFormat.format(new Date(e.date))),
      el('td', {}, e.type),
      el('td', {}, el('span', { class: 'tag ' + (e.success ? 'ok' : 'err') }, e.success ? 'succès' : 'échec')),
      el('td', {}, e.nif ?? '—'),
      el('td', {}, e.ip ?? '—'),
      el('td', {}, e.detail ?? ''),
    )));
  }

  onSubmit(eventsForm, async (filters) => { await loadEvents(filters); });

  await Promise.all([loadUsers(), loadResources(), loadEvents()]);
})();
