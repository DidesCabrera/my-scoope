import csv

from django.core.management.base import BaseCommand

from notas.domain.models import Food


class Command(BaseCommand):
    help = "Exporta foods a CSV con id y name"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="foods_export.csv",
            help="Ruta del archivo CSV de salida",
        )

    def handle(self, *args, **options):
        output_path = options["output"]

        foods = Food.objects.all().order_by("id").values_list("id", "name")

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name"])
            for food_id, name in foods:
                writer.writerow([food_id, name])

        self.stdout.write(
            self.style.SUCCESS(f"Archivo exportado correctamente: {output_path}")
        )