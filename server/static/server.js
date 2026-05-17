document.addEventListener("DOMContentLoaded", () => {
  const refreshButton = document.querySelector("[data-refresh]");
  if (refreshButton) {
    refreshButton.addEventListener("click", () => window.location.reload());
  }
});
