import csv
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from price_predictor.models import MasterProduct, DailyPriceHistory


BATCH_SIZE = 5_000
DATE_FORMAT = "%d/%m/%Y"   


class Command(BaseCommand):
    help = "Import data.csv into price_predictor_dailypricehistory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="data.csv",
            help="Path to the CSV file (default: data.csv in project root)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate CSV without writing to the database",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing records instead of skipping them",
        )

    def handle(self, *args, **options):
        csv_path = options["csv"]
        dry_run = options["dry_run"]
        do_update = options["update"]

        if not os.path.isfile(csv_path):
            raise CommandError(f"CSV file not found: {csv_path}")

        self.stdout.write(f"Reading: {csv_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved"))

        # Step 1: Count total rows for progress reporting 
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            total = sum(1 for _ in f) - 1  # subtract header
        self.stdout.write(f"Total data rows: {total:,}")

        # Step 2: Build product cache (commodityname → MasterProduct)
        self.stdout.write("Loading/creating MasterProduct entries...")
        product_cache = {}   # commodityname → MasterProduct instance

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["commodityname"].strip()
                unit = row["commodityunit"].strip()
                if name not in product_cache:
                    product_cache[name] = (name, unit)

        self.stdout.write(f"  Unique commodities found: {len(product_cache)}")

        if not dry_run:
            # get_or_create each unique product
            db_products = {}
            for name, unit in product_cache.values():
                obj, created = MasterProduct.objects.get_or_create(
                    commodityname=name,
                    defaults={"commodityunit": unit},
                )
                db_products[name] = obj
                if created:
                    self.stdout.write(f"  + Created MasterProduct: {name}")
        else:
            db_products = {}  # unused in dry run

        # Step 3: Stream CSV and bulk-insert DailyPriceHistory
        self.stdout.write("Importing DailyPriceHistory rows...")

        inserted = 0
        skipped = 0
        errors = 0
        batch = []

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for lineno, row in enumerate(reader, start=2):  # 2 = first data line
                # Parse & validate each field
                try:
                    name       = row["commodityname"].strip()
                    raw_date   = row["date"].strip()
                    min_price  = float(row["min_price"])
                    max_price  = float(row["max_price"])
                    avg_price  = float(row["avg_price"])
                    parsed_date: date = datetime.strptime(raw_date, DATE_FORMAT).date()
                except (KeyError, ValueError) as exc:
                    self.stderr.write(f"  Line {lineno}: skipped — {exc}")
                    errors += 1
                    continue

                if dry_run:
                    inserted += 1
                    continue

                product = db_products.get(name)
                if product is None:
                    # Safety fallback (shouldn't happen after step 2)
                    self.stderr.write(f"  Line {lineno}: unknown product '{name}', skipped")
                    skipped += 1
                    continue

                batch.append(
                    DailyPriceHistory(
                        product=product,
                        date=parsed_date,
                        min_price=min_price,
                        max_price=max_price,
                        avg_price=avg_price,
                    )
                )

                if len(batch) >= BATCH_SIZE:
                    saved, sk = self._flush(batch, do_update)
                    inserted += saved
                    skipped  += sk
                    batch = []
                    self.stdout.write(
                        f"  Progress: {inserted + skipped:,} / {total:,} rows processed"
                    )

        # Final partial batch
        if batch and not dry_run:
            saved, sk = self._flush(batch, do_update)
            inserted += saved
            skipped  += sk

        # Summary 
        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete. {inserted:,} valid rows, {errors} errors."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import complete!\n"
                    f"  Inserted : {inserted:,}\n"
                    f"  Skipped  : {skipped:,}  (duplicates or errors)\n"
                    f"  Errors   : {errors}"
                )
            )

    # Helper

    def _flush(self, batch: list, do_update: bool) -> tuple[int, int]:
        """Flush one batch to the DB. Returns (inserted, skipped)."""
        if do_update:
            # update_fields for all rows that already exist
            with transaction.atomic():
                for obj in batch:
                    DailyPriceHistory.objects.update_or_create(
                        product=obj.product,
                        date=obj.date,
                        defaults={
                            "min_price": obj.min_price,
                            "max_price": obj.max_price,
                            "avg_price": obj.avg_price,
                        },
                    )
            return len(batch), 0
        else:
            # ignore_conflicts silently skips rows that violate unique_together
            created = DailyPriceHistory.objects.bulk_create(
                batch, ignore_conflicts=True
            )
            inserted = len(created)
            skipped  = len(batch) - inserted
            return inserted, skipped