// Adapted from LovelyMiscLab's GPL-3.0 theme store: adds system mode + live OS updates.
import { create } from "zustand";
export type Theme = "light" | "dark";
export type ThemeMode = Theme | "system";
const KEY = "sentinel-workbench-theme";
const media = window.matchMedia("(prefers-color-scheme: dark)");
const resolve = (mode: ThemeMode): Theme =>
  mode === "system" ? (media.matches ? "dark" : "light") : mode;
const saved = localStorage.getItem(KEY);
const initial: ThemeMode =
  saved === "light" || saved === "dark" ? saved : "system";
function apply(mode: ThemeMode) {
  const theme = resolve(mode);
  document.documentElement.classList.toggle("dark", theme === "dark");
  localStorage.setItem(KEY, mode);
  void window.desktop?.theme(mode);
  return theme;
}
export const useThemeStore = create<{
  mode: ThemeMode;
  theme: Theme;
  setTheme: (mode: ThemeMode) => void;
}>((set) => ({
  mode: initial,
  theme: apply(initial),
  setTheme: (mode) => set({ mode, theme: apply(mode) }),
}));
media.addEventListener("change", () => {
  if (useThemeStore.getState().mode === "system")
    useThemeStore.setState({ theme: apply("system") });
});
