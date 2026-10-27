import type { Metadata } from "next";
import StationView from "@/components/StationView";

export const metadata: Metadata = { title: "Estación · Residente" };

export default function StationPage() {
  return <StationView />;
}
