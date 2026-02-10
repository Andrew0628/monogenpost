#!/usr/bin/env python3
"""Join Available.csv names with point values from AllValues.csv."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

ALL_VALUES_PATH = Path("AllValues.csv")
AVAILABLE_PATH = Path("Available.csv")
OUTPUT_PATH = Path("AvailableWithPoints.csv")


def find_name_column(fieldnames: list[str], *, file_label: str) -> str:
    """Find the name column, preferring 'Name' then first column containing 'name'."""
    exact_match = next((name for name in fieldnames if name == "Name"), None)
    if exact_match:
        return exact_match

    name_like = next((name for name in fieldnames if "name" in name.lower()), None)
    if name_like:
        return name_like

    raise ValueError(f"Could not find a name column in {file_label}.")


def is_numeric(value: str) -> bool:
    """Return whether value can be parsed as a number."""
    if value is None:
        return False
    value = value.strip()
    if value == "":
        return False
    try:
        float(value)
    except ValueError:
        return False
    return True


def find_points_column(fieldnames: list[str], rows: list[dict[str, str]]) -> str:
    """Find points column, preferring exact 'Points' then first numeric column."""
    exact_match = next((name for name in fieldnames if name == "Points"), None)
    if exact_match:
        return exact_match

    for column_name in fieldnames:
        values = [row.get(column_name, "") for row in rows]
        non_blank_values = [value for value in values if value is not None and value.strip() != ""]
        if non_blank_values and all(is_numeric(value) for value in non_blank_values):
            return column_name

    raise ValueError("Could not find a points column in AllValues.csv.")


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    last_error: UnicodeDecodeError | None = None

    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with path.open(newline="", encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                if not reader.fieldnames:
                    raise ValueError(f"{path} has no header row.")
                fieldnames = [name.strip() for name in reader.fieldnames]
                rows = []
                for row in reader:
                    cleaned = {}
                    for key, value in row.items():
                        if key is None:
                            continue
                        cleaned[key.strip()] = value.strip() if isinstance(value, str) else value
                    rows.append(cleaned)
            return fieldnames, rows
        except UnicodeDecodeError as exc:
            last_error = exc

    raise UnicodeDecodeError(
        last_error.encoding if last_error else "unknown",
        last_error.object if last_error else b"",
        last_error.start if last_error else 0,
        last_error.end if last_error else 0,
        f"Unable to decode {path} using attempted encodings",
    )


def warn_list(prefix: str, values: Iterable[str]) -> None:
    items = list(values)
    if items:
        print(f"WARNING: {prefix}: {', '.join(items)}")


def main() -> None:
    all_fields, all_rows = load_csv(ALL_VALUES_PATH)
    available_fields, available_rows = load_csv(AVAILABLE_PATH)

    all_name_column = find_name_column(all_fields, file_label=str(ALL_VALUES_PATH))
    available_name_column = find_name_column(available_fields, file_label=str(AVAILABLE_PATH))
    points_column = find_points_column(all_fields, all_rows)

    points_by_name: dict[str, str] = {}
    duplicate_names: list[str] = []

    for row in all_rows:
        name = row.get(all_name_column, "")
        if name in points_by_name:
            duplicate_names.append(name)
            continue
        points_by_name[name] = row.get(points_column, "")

    missing_names: list[str] = []
    output_rows: list[dict[str, str]] = []

    for row in available_rows:
        name = row.get(available_name_column, "")
        points = points_by_name.get(name, "")
        if points == "":
            missing_names.append(name)
        output_rows.append({"Name": name, "Points": points})

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["Name", "Points"])
        writer.writeheader()
        writer.writerows(output_rows)

    # Preserve first-seen order in warnings while suppressing duplicates in printout.
    unique_duplicates = list(dict.fromkeys(duplicate_names))
    unique_missing = list(dict.fromkeys(missing_names))

    warn_list("Duplicate names in AllValues.csv (using first occurrence)", unique_duplicates)
    warn_list("Names from Available.csv not found in AllValues.csv", unique_missing)

    print(f"Wrote {OUTPUT_PATH} with {len(output_rows)} rows.")


if __name__ == "__main__":
    main()
