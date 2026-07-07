module.exports = {
  apps: [
    {
      name: 'cognitive-loop-os-api',
      script: 'python',
      args: '-m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: __dirname,
      interpreter: 'none',
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      env: {
        PYTHONUNBUFFERED: '1'
      }
    },
    {
      name: 'hermes-sleep-loop-worker',
      script: 'python',
      args: 'scripts/sleep_loop_worker.py',
      cwd: __dirname,
      interpreter: 'none',
      autorestart: true,
      max_restarts: 20,
      min_uptime: '10s',
      out_file: 'logs/sleep-loop/pm2-worker-out.log',
      error_file: 'logs/sleep-loop/pm2-worker-error.log',
      merge_logs: true,
      env: {
        PYTHONUNBUFFERED: '1',
        SLEEP_LOOP_IDLE_SECONDS: '30'
      }
    }
  ]
};
