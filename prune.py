#!/usr/bin/env python3
"""
prune_dirs.py – prune date‑named backup directories with a simple GFS
(grandfather‑father‑son) retention policy inspired by **borg prune**.

Supported retention options
---------------------------
    --keep-daily N
    --keep-weekly N
    --keep-monthly N
    --keep-yearly N

The rules are processed in that order; once a directory is retained by an earlier
rule it is ignored by the later ones.
"""

import argparse
import datetime
from pathlib import Path
import re
import shutil
from collections import OrderedDict

# Period formats used to group dates
PRUNING_PATTERNS: OrderedDict[str, str] = OrderedDict(
    [
        ('daily', '%Y-%m-%d'),
        ('weekly', '%G-%V'),  # ISO week number
        ('monthly', '%Y-%m'),
        ('yearly', '%Y'),
    ]
)

DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')  # YYYY-MM-DD

DirEntry = tuple[datetime.date, Path, str]  # (date, path object, name)


def scan_directories(base: Path) -> list[DirEntry]:
    """Return a **descending** list of dated sub‑directories inside *base*."""
    items: list[DirEntry] = []
    for entry in base.iterdir():
        if entry.is_dir():
            try:
                ts = datetime.date.fromisoformat(entry.name)
            except ValueError:
                continue
            items.append((ts, entry, entry.name))
    items.sort(reverse=True)
    return items


def prune_split(
    items: list[DirEntry],
    rule: str,
    n: int,
    kept: set[str],
    kept_because: dict[str, tuple[str, int]],
) -> None:
    """Populate *kept* with directory names chosen by *rule*."""
    if n <= 0:
        return
    pattern = PRUNING_PATTERNS[rule]
    last_period = None
    counter = 0
    for ts, _, name in items:
        period = ts.strftime(pattern)
        if period != last_period:
            last_period = period
            if name not in kept:
                counter += 1
                kept.add(name)
                kept_because[name] = (rule, counter)
                if counter == n:
                    break


def choose_kept(items: list[DirEntry], args: argparse.Namespace):
    """Return (kept_names, reason_dict)."""
    kept: set[str] = set()
    because: dict[str, tuple[str, int]] = {}
    for rule in PRUNING_PATTERNS:
        prune_split(items, rule, getattr(args, rule), kept, because)
    return kept, because


def dir_size(path: Path) -> int:
    """Recursively calculate *path* size in bytes."""
    return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())


def format_size(bytes_: int):
    """Human‑readable binary size (GiB, MiB, …)."""
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    size = float(bytes_)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f'{size:,.1f} {unit}'
        size /= 1024


def main():
    p = argparse.ArgumentParser(
        description='Prune dated backup directories (YYYY‑MM‑DD) with GFS retention.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument('base', type=Path, help='Directory containing dated sub‑directories')
    p.add_argument('-d', '--keep-daily', dest='daily', type=int, default=0, help='Number of daily backups to keep')
    p.add_argument('-w', '--keep-weekly', dest='weekly', type=int, default=0, help='Number of weekly backups to keep')
    p.add_argument('-m', '--keep-monthly', dest='monthly', type=int, default=0, help='Number of monthly backups to keep')
    p.add_argument('-y', '--keep-yearly', dest='yearly', type=int, default=0, help='Number of yearly backups to keep')
    p.add_argument('-n', '--dry-run', action='store_true', help='Show what would be removed without deleting')

    args = p.parse_args()
    if not any((args.daily, args.weekly, args.monthly, args.yearly)):
        p.error('At least one of --keep-* rules should be provided')

    dirs = scan_directories(args.base)
    kept, because = choose_kept(dirs, args)
    total_bytes = 0

    prefix = '(DRYRUN) ' if args.dry_run else ''
    for _, path, name in dirs:
        if name in kept:
            rule, num = because[name]
            print(f'{prefix}KEEP   {name}   (rule: {rule} #{num})')
        else:
            size = dir_size(path)
            total_bytes += size
            size_h = format_size(size)
            print(f'{prefix}PRUNE  {name}   ({size_h})')
            if not args.dry_run:
                shutil.rmtree(path)

    print(f'\n{prefix}Removed {len(dirs) - len(kept)} directories totalling {format_size(total_bytes)}.')


if __name__ == '__main__':
    main()
