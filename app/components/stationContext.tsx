"use client";

import { createContext, useContext } from "react";

/** Whether this phone is linked to a reading station, and how to open a case there (UID only travels). */
export type StationApi = {
  linked: boolean;
  open: (caseId: string) => Promise<boolean>;
  link: (code: string) => Promise<string | null>; // null on success, else the error message
  unlink: () => Promise<void>;
};

export const StationContext = createContext<StationApi>({
  linked: false,
  open: async () => false,
  link: async () => "unavailable",
  unlink: async () => {},
});

export const useStation = () => useContext(StationContext);
