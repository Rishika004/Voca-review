import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/",
        destination: "/v2",
        permanent: false, // temporary redirect — easy to undo later
      },
    ];
  },
};

export default nextConfig;
