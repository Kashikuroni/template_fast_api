module.exports = {
  apps: [
    {
      name: 'fastapi-backend',
      script: '/root/.local/bin/uv',
      args:  'run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2',
      cwd:   '/var/www/forestriver/marketplaces-cms-backend',

      exec_mode: 'fork',
      instances: 1,

      env_file: './env/.env.production',
      env: { ENVIRONMENT: 'production' },

      error_file: './logs/err.log',
      out_file:   './logs/out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
};
