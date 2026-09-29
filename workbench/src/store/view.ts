import { create } from "zustand";
export type View =
  | "assets"
  | "intelligence"
  | "overview"
  | "events"
  | "code"
  | "runs"
  | "results"
  | "settings";
export const useViewStore = create<{ view: View; setView: (v: View) => void }>(
  (set) => ({ view: "overview", setView: (view) => set({ view }) }),
);
