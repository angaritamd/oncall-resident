import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], weight: ["300", "400", "500", "600"], variable: "--font-inter" });
const mono = JetBrains_Mono({ subsets: ["latin"], weight: ["500"], variable: "--font-jbm" });

const splash = [
  { w: 390, h: 844, r: 3 },
  { w: 393, h: 852, r: 3 },
  { w: 430, h: 932, r: 3 },
  { w: 375, h: 812, r: 3 },
];

export const metadata: Metadata = {
  title: "Residente",
  applicationName: "Residente",
  description: "Workflow tool, not a medical device. The radiologist decides and signs.",
  appleWebApp: {
    capable: true,
    title: "Residente",
    statusBarStyle: "default",
    startupImage: splash.map(({ w, h, r }) => ({
      url: `/splash/splash-${w * r}x${h * r}.png`,
      media: `(device-width: ${w}px) and (device-height: ${h}px) and (-webkit-device-pixel-ratio: ${r}) and (orientation: portrait)`,
    })),
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon.svg", type: "image/svg+xml" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#E9ECF0",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className={`${inter.variable} ${mono.variable} h-full antialiased`}>
      <body className="h-full">{children}</body>
    </html>
  );
}
