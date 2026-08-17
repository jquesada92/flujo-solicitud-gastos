-- Property-domain retirement migration
-- Date: 2026-08-17
--
-- IMPORTANT:
-- 1. Take and verify a database backup/snapshot before running this file.
-- 2. Apply and validate the application changes from this branch first in staging.
-- 3. This migration is intentionally NOT executed during application startup.
-- 4. A SQL downgrade cannot recover the data dropped here. Recovery requires
--    restoring the pre-migration backup/snapshot.

BEGIN;

-- Tables are dropped in dependency-safe order.
DROP TABLE IF EXISTS apartment_change_events;
DROP TABLE IF EXISTS user_apartments;
DROP TABLE IF EXISTS apartments;

-- Legacy property fields are no longer part of the User application model.
ALTER TABLE users DROP COLUMN IF EXISTS apartment_number;
ALTER TABLE users DROP COLUMN IF EXISTS person_type;

-- Drop enum types only after all dependent columns/tables are gone.
DROP TYPE IF EXISTS ownershiprole;
DROP TYPE IF EXISTS persontype;

COMMIT;

-- Post-migration validation examples:
-- SELECT to_regclass('public.apartments');
-- SELECT to_regclass('public.user_apartments');
-- SELECT to_regclass('public.apartment_change_events');
-- SELECT column_name FROM information_schema.columns
-- WHERE table_name='users' AND column_name IN ('apartment_number','person_type');
-- SELECT typname FROM pg_type WHERE typname IN ('ownershiprole','persontype');
