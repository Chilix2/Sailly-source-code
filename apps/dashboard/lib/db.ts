import { Pool } from 'pg';

let _pool: Pool | null = null;

export function getDbPool(): Pool {
  if (!_pool) {
    _pool = new Pool({
      connectionString: process.env.DATABASE_URL || 'postgresql://postgres@localhost:5433/sailly',
      max: 5,
    });
  }
  return _pool;
}
