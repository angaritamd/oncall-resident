import type { Metadata } from "next";
import BenchView from "@/components/BenchView";

export const metadata: Metadata = { title: "Benchmark RAD·QC · Residente" };

export default function BenchPage() {
  return <BenchView />;
}
