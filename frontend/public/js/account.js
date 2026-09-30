(async () => {
  const me = await requireSession();
  if (!me) return;

  document.getElementById('identity').textContent = 'Numéro fiscal ' + me.nif + ' · ' + (me.roles.join(', ') || 'aucun rôle');

  const profileForm = document.getElementById('profile-form');
  profileForm.email.value = me.email;
  profileForm.address.value = me.address;
  onSubmit(profileForm, async ({ email, address }) => {
    await api('PATCH', '/me', { email, address });
    return 'Informations mises à jour.';
  });

  onSubmit(document.getElementById('password-form'), async ({ current_password, new_password, confirm }, form) => {
    checkPassword(new_password, confirm);
    await api('POST', '/me/password', { current_password, new_password });
    form.reset();
    return 'Mot de passe modifié. Vos autres sessions ont été fermées.';
  });

  const setup = document.getElementById('totp-setup');
  onSubmit(document.getElementById('totp-renew-form'), async ({ password }, form) => {
    showQr(setup, await api('POST', '/me/totp/renew', { password }));
    form.reset();
    setup.querySelector('input').focus();
    return 'Scannez le QR code ci-dessous.';
  });

  onSubmit(document.getElementById('totp-confirm-form'), async ({ code }, form) => {
    await api('POST', '/me/totp/confirm', { code });
    form.reset();
    setup.querySelector('.qr').hidden = true;
    return 'Nouvelle application enregistrée.';
  });
})();
