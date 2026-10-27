import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Residente de turno",
    short_name: "Residente",
    description: "Workflow tool, not a medical device. The radiologist decides and signs.",
    start_url: "/",
    display: "standalone",
    background_color: "#121519",
    theme_color: "#121519",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
