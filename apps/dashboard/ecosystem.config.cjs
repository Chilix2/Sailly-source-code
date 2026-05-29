module.exports = {
  apps: [{
    name: "dashboard",
    script: ".next/standalone/server.js",
    cwd: "/home/charles2/sailly/apps/dashboard",
    env: {
      PORT: "3001",
      NODE_ENV: "production"
    },
    autorestart: true,
    max_memory_restart: "300M"
  }]
};
