import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    /**
     * Barrel-file optimisation: tree-shakes barrel re-exports so only the
     * icons / functions actually used end up in the client bundle.
     * Without this, lucide-react alone pulls in every icon module.
     */
    optimizePackageImports: [
      "lucide-react",
      "recharts",
      "date-fns",
      "react-hook-form",
      "@hookform/resolvers",
    ],
  },
};

export default nextConfig;
