// PM2 config — alternatif tanpa Docker, jalankan: pm2 start ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'koperasi-kyn',
      script: 'uvicorn',
      args: 'backend.main:app --host 0.0.0.0 --port 8002',
      interpreter: 'none',
      cwd: '/var/www/koperasi-kyn',
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      env: {
        APP_ENV: 'production',
      },
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      error_file: './logs/err.log',
      out_file: './logs/out.log',
      merge_logs: true,
    },
  ],
}
