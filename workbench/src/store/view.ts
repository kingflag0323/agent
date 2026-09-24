import { create } from "zustand";
export type View =
  | "assets"
  | "intelligence"
  | "overview"
  | "events"
  | "canvas"
  | "code"
  | "runs"
  | "settings";
export const useViewStore = create<{ view: View; setView: (v: View) => void }>(
  (set) => ({ view: "overview", setView: (view) => set({ view }) }),
);
