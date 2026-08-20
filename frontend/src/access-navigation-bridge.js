const ACCESS_HASH = "#access-management";

function shouldLeaveAccessConsole(button) {
  if (!button || button.dataset.iamAccess === "true") return false;

  const configMenu = button.closest(".config-menu");
  const configItems = button.closest(".config-menu-items");

  // Opening/closing the Configuración dropdown is not navigation by itself.
  if (configMenu && !configItems) return false;

  return true;
}

function leaveAccessConsoleOnTopbarNavigation(event) {
  if (window.location.hash !== ACCESS_HASH) return;

  const target = event.target instanceof Element ? event.target : null;
  const button = target?.closest(".topbar button");
  if (!shouldLeaveAccessConsole(button)) return;

  // Clear the hash in capture phase so the IAM overlay is removed even when
  // the underlying React tab is already the requested destination (for
  // example, Accesos was opened while Inicio was the active tab).
  window.location.hash = "";
}

document.addEventListener("click", leaveAccessConsoleOnTopbarNavigation, true);
