# Database Migrations

Sistem migration untuk WireGuard VPN Backend menggunakan SQL files dengan tracking di database.

## Struktur

```
database/migrations/
├── __init__.py
├── migration_runner.py      # Script untuk menjalankan migrations
├── README.md                # File ini
├── 001_initial_schema.sql   # Base schema (reference ke schema.sql)
├── 002_add_qr_expiration.sql
└── 003_add_performance_indexes.sql
```

## Migration Files

Migration files harus dijalankan secara berurutan berdasarkan prefix angka:

1. **001_initial_schema.sql** - Base schema (sudah ada di `database/schema.sql`)
   - Tabel: `vpn_devices`, `vpn_traffic_logs`, `vpn_revoke_history`, `vpn_bandwidth_limits`, `vpn_audit_logs`
   - Biasanya sudah dijalankan manual saat setup awal

2. **002_add_qr_expiration.sql** - Add QR Code Expiration Support
   - Menambah kolom `qr_code_base64` dan `qr_code_expires_at` ke `vpn_devices`
   - Phase 7: QR Code Expiration & Security Enhancements

3. **003_add_performance_indexes.sql** - Add Performance Indexes
   - Menambah berbagai index untuk optimasi query
   - Phase 8: Performance Optimization & Caching

## Menjalankan Migrations

### 1. Manual (Recommended untuk Production)

```bash
# Dari root project
python -m database.migrations.migration_runner

# Atau dengan path lengkap
python database/migrations/migration_runner.py
```

### 2. Dry Run (Preview tanpa eksekusi)

```bash
python -m database.migrations.migration_runner --dry-run
```

### 3. List Status Migrations

```bash
python -m database.migrations.migration_runner --list
```

### 4. Dari Python Code

```python
from database.migrations import run_all_migrations, list_migrations

# Run all pending migrations
run_all_migrations()

# List migration status
list_migrations()
```

## Tracking

Migrations yang sudah dijalankan ditrack di tabel `schema_migrations`:

```sql
CREATE TABLE schema_migrations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    migration_file VARCHAR(255) NOT NULL UNIQUE,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Migration yang sudah dijalankan tidak akan dijalankan lagi (idempotent).

## Membuat Migration Baru

1. Buat file SQL baru dengan format: `XXX_description.sql`
   - `XXX` = nomor urut (004, 005, dst)
   - `description` = deskripsi singkat migration

2. Gunakan `IF NOT EXISTS` untuk statements yang bisa dijalankan berulang:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_example ON table_name(column);
   ALTER TABLE table_name ADD COLUMN IF NOT EXISTS new_column VARCHAR(100);
   ```

3. Test migration dengan dry-run:
   ```bash
   python -m database.migrations.migration_runner --dry-run
   ```

4. Jalankan migration:
   ```bash
   python -m database.migrations.migration_runner
   ```

## Best Practices

1. **Selalu test di development dulu** sebelum production
2. **Backup database** sebelum menjalankan migration di production
3. **Gunakan IF NOT EXISTS** untuk statements yang idempotent
4. **Satu migration = satu perubahan logis** (jangan gabung banyak perubahan)
5. **Dokumentasikan** perubahan di header file migration
6. **Test rollback** jika perlu (manual restore dari backup)

## Troubleshooting

### Migration gagal di tengah jalan

1. Check error message di log
2. Fix masalah di database manual jika perlu
3. Jika migration sudah ter-track tapi gagal, hapus dari `schema_migrations`:
   ```sql
   DELETE FROM schema_migrations WHERE migration_file = 'XXX_description.sql';
   ```
4. Fix migration file dan jalankan lagi

### Migration sudah dijalankan tapi perlu di-rollback

1. Backup database
2. Restore dari backup atau jalankan rollback manual
3. Hapus dari tracking:
   ```sql
   DELETE FROM schema_migrations WHERE migration_file = 'XXX_description.sql';
   ```

### Check migration status

```bash
# Via script
python -m database.migrations.migration_runner --list

# Via SQL
SELECT * FROM schema_migrations ORDER BY applied_at;
```

## Integration dengan Deployment

### Manual (Recommended)

Jalankan migration manual setelah deploy:

```bash
# Setelah pull code baru
git pull
python -m database.migrations.migration_runner
# Restart aplikasi
```

### Automatic (Opsional)

Bisa diintegrasikan di `app/main.py` startup event:

```python
@app.on_event("startup")
async def startup():
    # ... existing code ...
    
    # Run migrations (opsional - hati-hati di production!)
    from database.migrations import run_all_migrations
    try:
        run_all_migrations()
        logger.info("Database migrations completed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Decide: exit or continue?
```

**Note:** Auto-migration di startup tidak direkomendasikan untuk production karena:
- Tidak ada kontrol manual
- Sulit rollback jika ada masalah
- Bisa menyebabkan downtime

## Migration History

| File | Description | Phase | Applied |
|------|-------------|-------|---------|
| 001_initial_schema.sql | Base schema | Phase 1 | Manual setup |
| 002_add_qr_expiration.sql | QR expiration support | Phase 7 | - |
| 003_add_performance_indexes.sql | Performance indexes | Phase 8 | - |
