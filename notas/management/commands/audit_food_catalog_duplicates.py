from django.core.management.base import BaseCommand, CommandError

from notas.application.services.food_catalog_duplicate_cleanup import audit_food_catalog_duplicates


class Command(BaseCommand):
    help = "Audit global notas.Food duplicates; --apply retires duplicate catalog snapshots."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Retire duplicate global snapshots.")

    def handle(self, *args, **options):
        audit = audit_food_catalog_duplicates(apply=options["apply"])
        for group in audit.groups:
            self.stdout.write(
                f"catalog_id={group.catalog_food_id} catalog_ref={group.catalog_food_ref} "
                f"keep={group.survivor_id} retire={','.join(map(str, group.retired_ids))}"
            )
        for conflict in audit.conflicts:
            self.stderr.write(f"CONFLICT: {conflict}")
        for name, count in audit.possible_name_duplicates:
            self.stdout.write(f"REVIEW canonical_name={name!r} active_global_rows={count}")
        self.stdout.write(
            f"snapshot_duplicate_groups={len(audit.groups)} retired={audit.retired_count} "
            f"conflicts={len(audit.conflicts)} possible_name_duplicates={len(audit.possible_name_duplicates)}"
        )
        if audit.conflicts and options["apply"]:
            raise CommandError("Conflicting catalog identities require manual review; no rows were changed.")
