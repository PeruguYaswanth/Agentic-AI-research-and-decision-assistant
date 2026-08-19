/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://agentic-ai-research-and-decision.onrender.com/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig