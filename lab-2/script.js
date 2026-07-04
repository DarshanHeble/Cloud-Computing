document.addEventListener('DOMContentLoaded', () => {
  const lastUpdated = document.getElementById('last-updated');
  const toggleTheme = document.getElementById('toggle-theme');

  if (lastUpdated) {
    lastUpdated.textContent = new Date().toLocaleString();
  }

  if (toggleTheme) {
    toggleTheme.addEventListener('click', () => {
      document.body.classList.toggle('highlight-mode');
      toggleTheme.textContent = document.body.classList.contains('highlight-mode')
        ? 'Disable highlight mode'
        : 'Toggle highlight mode';
    });
  }
});
