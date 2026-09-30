(async () => {
  // Page réservée aux rôles autorisés sur la ressource « taux » (configurés par l'administrateur)
  try {
    await api('GET', '/access/taux');
  } catch (error) {
    if (error.status === 401) return goLogin();
    location.href = '/services.html';
    return;
  }
  const me = await requireSession();
  if (!me) return;

  const dateFormat = new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  const updated = (t) => (t.updated_at ? dateFormat.format(new Date(t.updated_at)) + (t.updated_by ? ' · ' + t.updated_by : '') : '—');

  /** Ligne d'un contribuable : formulaire de modification de son taux. */
  function row(t) {
    const when = el('td', {}, updated(t));
    const form = el('form', { class: 'rate' },
      el('input', { name: 'rate', type: 'number', min: 0, max: 60, step: 0.1, value: t.rate ?? '', required: true,
                    'aria-label': 'Taux de ' + t.nif }),
      el('button', { type: 'submit', class: 'ghost small' }, 'Enregistrer'),
      el('p', { class: 'msg', role: 'status' }));
    onSubmit(form, async ({ rate }) => {
      await api('PUT', `/tax/taxpayers/${t.nif}`, { rate: Number(rate) });
      when.textContent = updated({ updated_at: new Date(), updated_by: me.nif });
      return 'Enregistré';
    });
    return el('tr', {}, el('td', {}, t.nif), el('td', {}, t.email), when, el('td', {}, form));
  }

  async function load({ nif = '' } = {}) {
    const taxpayers = await api('GET', '/tax/taxpayers?' + new URLSearchParams({ nif }));
    document.getElementById('taxpayers').replaceChildren(...taxpayers.map(row));
    document.getElementById('empty').hidden = taxpayers.length > 0;
  }

  onSubmit(document.getElementById('search-form'), load);
  await load();
})();
