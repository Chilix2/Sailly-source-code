/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  async redirects() {
    return [
      {
        source: '/builder-legacy-backup',
        destination: '/builder',
        permanent: false,
      },
      {
        source: '/builder-legacy-backup/:path*',
        destination: '/builder',
        permanent: false,
      },
      {
        source: '/builder/workflows',
        destination: '/builder',
        permanent: false,
      },
      {
        source: '/builder/scenarios',
        destination: '/builder',
        permanent: false,
      },
      {
        source: '/builder/lab',
        destination: '/builder',
        permanent: false,
      },
      {
        source: '/builder/tenants/new',
        destination: '/tenants/new',
        permanent: false,
      },
    ];
  },
  async rewrites() {
    const validationOrigin =
      process.env.VALIDATION_DASHBOARD_ORIGIN || 'http://127.0.0.1:8090';
    const voiceAgentOrigin =
      process.env.VOICE_AGENT_ORIGIN || 'http://127.0.0.1:8080';
    return [
      {
        source: '/validation-static/:path*',
        destination: `${validationOrigin.replace(/\/$/, '')}/:path*`,
      },
      {
        source: '/api/builder/:path*',
        destination: `${voiceAgentOrigin.replace(/\/$/, '')}/api/builder/:path*`,
      },
    ];
  },
};

export default nextConfig;

