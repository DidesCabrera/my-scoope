import csv

from django.core.management.base import BaseCommand

from notas.domain.models import Food


class Command(BaseCommand):
    help = "Exporta todas las columnas propias de Food a CSV, excluyendo relaciones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            default="foods_full_export.csv",
            help="Ruta del archivo CSV de salida",
        )

    def handle(self, *args, **options):
        output_path = options["output"]

        model_fields = []
        header = []

        for field in Food._meta.concrete_fields:
            model_fields.append(field)

            if field.is_relation:
                header.append(field.attname)   # ej: created_by_id
            else:
                header.append(field.name)      # ej: id, name, protein

        queryset = Food.objects.all().order_by("id")

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(header)

            for food in queryset:
                row = []
                for field in model_fields:
                    if field.is_relation:
                        row.append(getattr(food, field.attname))
                    else:
                        row.append(getattr(food, field.name))
                writer.writerow(row)

        self.stdout.write(
            self.style.SUCCESS(
                f"Archivo exportado correctamente: {output_path}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Columnas exportadas: {', '.join(header)}"
            )
        )