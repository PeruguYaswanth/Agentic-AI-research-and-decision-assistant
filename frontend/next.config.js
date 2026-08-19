/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const isProduction = process.env.NODE_ENV === 'production'
    const backendUrl = isProduction
      ? 'https://agentic-ai-research-and-decision.onrender.com'
      : 'http://127.0.0.1:8000'

    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig