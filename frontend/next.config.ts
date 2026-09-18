import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL || "https://archimedes-energy-backend.onrender.com";
    const target = backendUrl.replace(/\/+$/, "");
    return [
      {
        source: "/api/py/:path*",
        destination: `${target}/:path*`,
      },
    ];
  },
};

export default nextConfig;
