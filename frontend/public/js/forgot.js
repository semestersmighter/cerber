onSubmit(document.getElementById('forgot-form'), async ({ nif, code, new_password, confirm }, form) => {
  checkPassword(new_password, confirm);
  await api('POST', '/auth/password/forgot', { nif, code, new_password });
  form.reset();
  setTimeout(() => { location.href = '/'; }, 2000);
  return 'Mot de passe réinitialisé. Redirection vers la connexion…';
});
