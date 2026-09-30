// Étape 1 : NIF + mot de passe, puis page du code TOTP
onSubmit(document.getElementById('login-form'), async ({ nif, password }) => {
  const { totp_enrolled } = await api('POST', '/auth/login', { nif, password });
  const params = new URLSearchParams();
  if (!totp_enrolled) params.set('setup', '1');
  if (nextPage()) params.set('next', nextPage());
  location.href = '/mfa.html' + (params.toString() ? '?' + params : '');
});
