/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  async rewrites() {
    const backendUrl =
      process.env.NODE_ENV === 'development'
        ? 'http://127.0.0.1:8000'
        : 'https://agentic-ai-research-and-decision.onrender.com'

    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig