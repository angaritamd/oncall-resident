"use client";

import { createContext, useContext } from "react";

/** Whether this phone is linked to a reading station, and how to open a case there (UID only travels). */
export type OpenResult = { ok: true } | { ok: false; message: string };

export type StationApi = {
  linked: boolean | null; // null = unknown (could not ask the core); never shown as "not linked"
  refresh: () => void;
  open: (caseId: string) => Promise<OpenResult>;
  link: (code: string) => Promise<string | null>; // null on success, else the error message
  unlink: () => Promise<string | null>;
};

export const StationContext = createContext<StationApi>({
  linked: false,
  refresh: () => {},
  open: async () => ({ ok: false, message: "" }),
  link: async () => "unavailable",
  unlink: async () => null,
});

export const useStation = () => useContext(StationContext);
