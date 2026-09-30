// Étape 2 : code TOTP (et, à la première connexion, affichage du QR code)
const setupSection = document.getElementById('setup');

if (new URLSearchParams(location.search).has('setup')) {
  document.getElementById('intro').textContent =
    "Première connexion : scannez ce QR code avec votre application d'authentification " +
    '(Google Authenticator, FreeOTP, Microsoft Authenticator…), puis saisissez le code affiché.';
  api('GET', '/auth/totp/setup')
    .then((setup) => showQr(setupSection, setup))
    .catch(() => { location.href = '/'; });
}

onSubmit(document.getElementById('mfa-form'), async ({ code }) => {
  try {
    await api('POST', '/auth/mfa', { code });
  } catch (error) {
    // Délai dépassé ou compte verrouillé : retour à la connexion
    if (error.status === 401 && !/Code/.test(error.message)) setTimeout(() => { location.href = '/'; }, 1500);
    if (error.status === 423) setTimeout(() => { location.href = '/'; }, 2500);
    throw error;
  }
  location.href = nextPage() || '/services.html';
});
