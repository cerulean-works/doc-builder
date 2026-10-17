/**
 * The Daylight / Evening appearance. `app.html` applies the stored preference before first paint
 * by toggling `:root.dark-theme`; this module keeps components in sync with that class.
 */
export const STORAGE_KEY = "cerulean-theme";

export const theme = $state({ dark: true });

/** Reads the class the pre-paint script set. Call from `onMount`. */
export function syncTheme() {
	theme.dark = document.documentElement.classList.contains("dark-theme");
}

export function toggleTheme() {
	theme.dark = document.documentElement.classList.toggle("dark-theme");
	try {
		localStorage.setItem(STORAGE_KEY, theme.dark ? "dark" : "light");
	} catch {
		// The toggle still works when storage is unavailable.
	}
}
