#!/usr/bin/env python3
"""
Migrate existing scanner_performance.csv to add new alpha columns

This script safely adds the new columns (spy_return, alpha, sector_return)
to existing CSV data without losing any information.

Usage:
    python3 migrate_scanner_csv.py
"""

import csv
from pathlib import Path
from datetime import datetime

WORKSPACE = Path('/Users/mikeclawd/.openclaw/workspace')
SCANNER_PERFORMANCE_FILE = WORKSPACE / 'data/scanner_performance.csv'
BACKUP_FILE = WORKSPACE / 'data/scanner_performance_backup.csv'

# Old headers (before alpha enhancement)
OLD_HEADERS = [
    'scan_date', 'scan_time', 'symbol', 'price_at_scan', 'scanner_score',
    'float_score', 'momentum_score', 'volume_score', 'catalyst_score', 'multiday_score',
    'vigl_bonus', 'vigl_match', 'rvol',
    'float_shares', 'change_pct', 'volume', 'catalyst_text',
    'entered', 'entry_date', 'entry_price', 'entry_thesis',
    'exit_date', 'exit_price', 'hold_days', 'return_pct', 'return_dollars',
    'outcome', 'notes'
]

# New headers (with alpha columns)
NEW_HEADERS = [
    'scan_date', 'scan_time', 'symbol', 'price_at_scan', 'scanner_score',
    'float_score', 'momentum_score', 'volume_score', 'catalyst_score', 'multiday_score',
    'vigl_bonus', 'vigl_match', 'rvol',
    'float_shares', 'change_pct', 'volume', 'catalyst_text',
    'entered', 'entry_date', 'entry_price', 'entry_thesis',
    'exit_date', 'exit_price', 'hold_days', 'return_pct', 'return_dollars',
    'spy_return', 'alpha', 'sector_return',
    'outcome', 'notes'
]


def migrate_csv():
    """Migrate CSV to new format with alpha columns"""

    if not SCANNER_PERFORMANCE_FILE.exists():
        print("❌ No scanner_performance.csv file found")
        print("   Nothing to migrate - new file will be created on first use")
        return

    print("Scanner Performance CSV Migration")
    print("=" * 60)

    # Create backup
    import shutil
    backup_path = BACKUP_FILE.with_name(f"scanner_performance_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    shutil.copy2(SCANNER_PERFORMANCE_FILE, backup_path)
    print(f"✅ Created backup: {backup_path.name}")

    # Read existing data
    rows = []
    with open(SCANNER_PERFORMANCE_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        existing_headers = reader.fieldnames

        # Check if migration is needed
        if 'spy_return' in existing_headers and 'alpha' in existing_headers:
            print("✅ CSV already has alpha columns - no migration needed")
            return

        for row in reader:
            # Add new columns with empty values
            row['spy_return'] = row.get('spy_return', '')
            row['alpha'] = row.get('alpha', '')
            row['sector_return'] = row.get('sector_return', '')
            rows.append(row)

    print(f"📊 Found {len(rows)} existing records")

    # Write back with new headers
    with open(SCANNER_PERFORMANCE_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=NEW_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Migration complete - added 3 new columns")
    print(f"   - spy_return")
    print(f"   - alpha")
    print(f"   - sector_return")
    print()
    print("Note: Alpha will be calculated automatically for future trade closures")
    print("      Existing closed trades will have empty alpha values")
    print()
    print("=" * 60)


if __name__ == '__main__':
    migrate_csv()
