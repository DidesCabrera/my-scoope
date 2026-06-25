import os
import pandas as pd


def export_directory_to_excel(
    base_path: str,
    output_path: str,
    exclude_dirs=None
):
    """
    Genera un archivo Excel con la estructura de directorios.

    - Cada fila representa un archivo
    - Cada columna representa un nivel de profundidad
    """

    if exclude_dirs is None:
        exclude_dirs = ["__pycache__"]

    rows = []

    for root, dirs, files in os.walk(base_path):
        # Excluir carpetas no deseadas
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        rel_path = os.path.relpath(root, base_path)
        depth = [] if rel_path == "." else rel_path.split(os.sep)

        for file in files:
            rows.append(depth + [file])

    if not rows:
        raise ValueError("No se encontraron archivos en la ruta indicada.")

    max_depth = max(len(r) for r in rows)
    normalized = [r + [""] * (max_depth - len(r)) for r in rows]

    columns = [f"Nivel {i + 1}" for i in range(max_depth)]
    df = pd.DataFrame(normalized, columns=columns)

    df.to_excel(output_path, index=False)
    print(f"Archivo generado: {output_path}")


if __name__ == "__main__":
    export_directory_to_excel(
        base_path="notas",#<<AQUI--------------------------------
        output_path="estructura_directorio.xlsx"
    )
