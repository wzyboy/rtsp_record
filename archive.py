#!/usr/bin/env python

import re
import argparse
from pathlib import Path
from datetime import datetime
from datetime import timedelta

from collections.abc import Iterator


class Archiver:
    TS_FMT = '%Y-%m-%d_%H-%M-%S'
    TS_RE = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}'

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        now = datetime.now()
        self.threshold = now - timedelta(minutes=60)

    def iter_mv_pair(self) -> Iterator[tuple[Path, Path]]:
        matched_any = False
        for path in self.base_dir.glob('*.mkv'):
            if matched := re.search(self.TS_RE, path.stem):
                ts = datetime.strptime(matched.group(0), self.TS_FMT)
                if ts < self.threshold:
                    new_path = self.base_dir / ts.strftime('%Y-%m-%d') / path.name
                    matched_any = True
                    yield (path, new_path)
        if not matched_any:
            raise SystemExit('No matching files found.')

    def archive(self, dry_run: bool = False) -> None:
        for path, new_path in self.iter_mv_pair():
            if new_path.exists():
                raise FileExistsError(new_path)
            print(f'{path} => {new_path}')
            if not dry_run:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                path.rename(new_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base_dir', type=Path)
    ap.add_argument('-n', '--dry-run', action='store_true')
    args = ap.parse_args()

    archiver = Archiver(args.base_dir)
    archiver.archive(args.dry_run)


if __name__ == '__main__':
    main()
