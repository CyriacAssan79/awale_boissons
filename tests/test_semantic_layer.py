"""Tests de docs/semantic_layer.yml.

1. Les définitions des KPI de la Partie A sont identiques, mot pour mot, à celles de
   docs/business_problem.ipynb.
2. Chaque expression s'exécute réellement contre la base DuckDB et respecte ses bornes.

La base est celle de AWALE_DUCKDB_PATH (défaut : data/awale.duckdb). Si elle est absente
ou verrouillée par un autre programme, les tests qui en ont besoin sont ignorés (et non
validés) : fermer l'aperçu DuckDB de l'éditeur avant de lancer pytest.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
LAYER_FILE = ROOT / "docs" / "semantic_layer.yml"
BUSINESS_NOTEBOOK = ROOT / "docs" / "business_problem.ipynb"

REQUIRED_KEYS = {"libelle", "definition", "modele", "expression", "dimensions", "unite"}


@pytest.fixture(scope="module")
def layer() -> dict:
    return yaml.safe_load(LAYER_FILE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def con():
    duckdb = pytest.importorskip("duckdb")

    path = Path(os.environ.get("AWALE_DUCKDB_PATH", ROOT / "data" / "awale.duckdb"))
    if not path.exists():
        pytest.skip(f"base introuvable : {path}")

    try:
        connection = duckdb.connect(str(path), read_only=True)
    except duckdb.Error as error:
        pytest.skip(f"base inaccessible (verrouillée ?) : {str(error).splitlines()[0]}")

    yield connection
    connection.close()


def business_kpi_definitions() -> dict[str, str]:
    """{nom du KPI: définition} lus dans la section 5 de business_problem.ipynb."""
    notebook = json.loads(BUSINESS_NOTEBOOK.read_text(encoding="utf-8"))
    definitions: dict[str, str] = {}

    for cell in notebook["cells"]:
        source = cell["source"]
        text = source if isinstance(source, str) else "".join(source)

        for line in text.splitlines():
            match = re.match(r"^- \*\*(.+?)\*\* : (.+)$", line.strip())
            if match:
                definitions[match.group(1)] = match.group(2).strip()

    return definitions


# ---------------------------------------------------------------------------
# Cohérence avec la Partie A (sans base de données)
# ---------------------------------------------------------------------------

def test_every_metric_has_the_required_keys(layer):
    for name, metric in layer["metriques"].items():
        missing = REQUIRED_KEYS - set(metric)
        assert not missing, f"{name} : clés manquantes {sorted(missing)}"


def test_part_a_kpis_match_business_problem_word_for_word(layer):
    expected = business_kpi_definitions()
    assert len(expected) == 8, f"8 KPI attendus dans business_problem, trouvés : {list(expected)}"

    in_layer = {
        m["kpi_partie_a"]: m["definition"]
        for m in layer["metriques"].values()
        if "kpi_partie_a" in m
    }

    assert set(in_layer) == set(expected), (
        f"KPI absents de la couche sémantique : {sorted(set(expected) - set(in_layer))} ; "
        f"en trop : {sorted(set(in_layer) - set(expected))}"
    )

    for name, definition in expected.items():
        assert in_layer[name] == definition, (
            f"Définition différente pour « {name} » :\n"
            f"  business_problem : {definition}\n  semantic_layer   : {in_layer[name]}"
        )


def test_unsupported_kpis_are_declared(layer):
    assert {"attribution_causale_par_canal", "chiffre_d_affaires_livraison"} <= set(
        layer["non_soutenus"]
    )
    for entry in layer["non_soutenus"].values():
        assert entry["pourquoi"] and entry["il_faudrait"]


# ---------------------------------------------------------------------------
# Exécution réelle contre la base
# ---------------------------------------------------------------------------

def metric_names():
    return list(yaml.safe_load(LAYER_FILE.read_text(encoding="utf-8"))["metriques"])


@pytest.mark.parametrize("name", metric_names())
def test_expression_runs_and_respects_its_bounds(name, layer, con):
    metric = layer["metriques"][name]

    rows = con.execute(
        f"SELECT {metric['expression']} AS value FROM {metric['modele']}"
    ).fetchall()

    values = [r[0] for r in rows if r[0] is not None]
    assert rows, f"{name} : aucune ligne"
    assert values, f"{name} : valeur NULL sur toutes les lignes"

    if not metric.get("par_ligne"):
        assert len(rows) == 1

    bounds = metric.get("attendu", {}).get("entre")
    if bounds:
        low, high = bounds
        for value in values:
            assert low <= float(value) <= high, f"{name} = {value}, attendu entre {low} et {high}"


@pytest.mark.parametrize("name", metric_names())
def test_dimensions_exist_in_the_model(name, layer, con):
    metric = layer["metriques"][name]
    columns = {
        row[0]
        for row in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            [metric["modele"]],
        ).fetchall()
    }

    unknown = [d for d in metric["dimensions"] if d not in columns]
    assert not unknown, f"{name} : dimensions absentes de {metric['modele']} : {unknown}"
