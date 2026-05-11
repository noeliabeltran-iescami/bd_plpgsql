#!/usr/bin/env python3
import argparse
import os
import re
import sys
from pathlib import Path

try:
    import openai
except ImportError:
    openai = None

OBJECT_RE = re.compile(
    r"(?is)\bCREATE\s+(OR\s+REPLACE\s+)?(FUNCTION|PROCEDURE|TRIGGER|VIEW|TYPE)\s+([\w\.\"]+)(\s*\([^;]*?\))?\s*(RETURNS\s+[^;]+?)?\s*AS\b",
    re.MULTILINE,
)
NEXT_CREATE_RE = re.compile(r"(?is)\bCREATE\s+(OR\s+REPLACE\s+)?(FUNCTION|PROCEDURE|TRIGGER|VIEW|TYPE)\b")


def find_sql_files(path: Path):
    if path.is_file():
        return [path]
    files = []
    for child in path.rglob("*.sql"):
        if child.is_file():
            files.append(child)
    for child in path.rglob("*.pgsql"):
        if child.is_file():
            files.append(child)
    return sorted(files)


def extract_objects(sql_text: str):
    objs = []
    for match in OBJECT_RE.finditer(sql_text):
        start = match.start()
        rest = sql_text[start:]
        next_match = NEXT_CREATE_RE.search(rest, len(match.group(0)))
        end = start + next_match.start() if next_match else len(sql_text)
        body = sql_text[start:end].strip()
        obj_type = match.group(2).upper()
        obj_name = match.group(3).strip()
        signature = match.group(4) or ""
        returns = match.group(5) or ""
        objs.append({
            "type": obj_type,
            "name": obj_name,
            "signature": signature.strip(),
            "returns": returns.strip(),
            "body": body,
        })
    return objs


def render_markdown(objects, ai_output=False):
    lines = ["# Documentación PL/pgSQL generada", ""]
    if ai_output:
        lines.append(
            "_Este documento contiene descripciones sugeridas por IA cuando la opción `--ai` estaba habilitada._"
        )
        lines.append("")
    for obj in objects:
        lines.append(f"## {obj['name']} ({obj['type']})")
        lines.append("")
        lines.append(f"**Tipo:** {obj['type']}")
        if obj.get("signature"):
            lines.append(f"**Firma:** `{obj['name']}{obj['signature']}`")
        if obj.get("returns"):
            lines.append(f"**Retorna:** {obj['returns']}")
        lines.append("")
        if obj.get("ai_documentation"):
            lines.append(obj["ai_documentation"].strip())
        else:
            lines.append("**Descripción:**")
            lines.append("")
            lines.append(
                "Se ha extraído el objeto PL/pgSQL. Añade una descripción personalizada o usa `--ai` para generar texto con IA."
            )
            lines.append("")
        lines.append("### SQL\n")
        lines.append("```sql")
        lines.append(obj["body"].strip())
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def call_openai(prompt, model="gpt-3.5-turbo", max_tokens=512):
    if not openai:
        raise RuntimeError("La biblioteca openai no está instalada.")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("La variable de entorno OPENAI_API_KEY no está definida.")
    openai.api_key = api_key
    completion = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "Eres un asistente técnico que genera documentación clara y breve para objetos PL/pgSQL."},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return completion.choices[0].message.content.strip()


def build_prompt(obj):
    return (
        f"Genera una documentación concisa en español para el siguiente objeto PL/pgSQL:\n\n"
        f"Tipo: {obj['type']}\n"
        f"Nombre: {obj['name']}\n"
        f"Firma: {obj['signature']}\n"
        f"Retorna: {obj['returns']}\n\n"
        f"Código:\n{obj['body']}\n\n"
        "Incluye:\n"
        "- Una breve descripción del objeto.\n"
        "- Los parámetros de entrada y su significado, si aplica.\n"
        "- El valor devuelto, si aplica.\n"
        "- Cualquier detalle importante de uso o comportamiento.\n"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Genera documentación Markdown para objetos PL/pgSQL de PostgreSQL."
    )
    parser.add_argument("--src", required=True, help="Archivo SQL o carpeta con .sql/.pgsql")
    parser.add_argument("--output", default="docs/plpgsql_documentation.md", help="Ruta de salida Markdown")
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Usar IA para generar descripciones cuando OPENAI_API_KEY esté configurada.",
    )
    parser.add_argument(
        "--model",
        default="gpt-3.5-turbo",
        help="Modelo OpenAI a usar cuando se habilita --ai.",
    )
    args = parser.parse_args()

    src_path = Path(args.src).resolve()
    if not src_path.exists():
        print(f"ERROR: No existe la ruta {src_path}", file=sys.stderr)
        sys.exit(1)

    paths = find_sql_files(src_path)
    if not paths:
        print(f"ERROR: No se encontraron archivos SQL en {src_path}", file=sys.stderr)
        sys.exit(1)

    all_objects = []
    for file_path in paths:
        text = file_path.read_text(encoding="utf-8")
        objects = extract_objects(text)
        if objects:
            all_objects.extend(objects)

    if not all_objects:
        print("ERROR: No se han detectado objetos PL/pgSQL válidos en los archivos.", file=sys.stderr)
        sys.exit(1)

    if args.ai:
        if not openai:
            print(
                "Advertencia: openai no está instalado. Instalalo con `pip install openai` y vuelve a ejecutar con --ai.",
                file=sys.stderr,
            )
        else:
            for obj in all_objects:
                try:
                    prompt = build_prompt(obj)
                    obj["ai_documentation"] = call_openai(prompt, model=args.model)
                except Exception as exc:
                    print(f"Advertencia: no se pudo generar IA para {obj['name']}: {exc}", file=sys.stderr)
                    obj["ai_documentation"] = "No se pudo generar documentación IA; usa la extracción básica."

    output_text = render_markdown(all_objects, ai_output=args.ai)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")
    print(f"Generado: {output_path}")


if __name__ == "__main__":
    main()
