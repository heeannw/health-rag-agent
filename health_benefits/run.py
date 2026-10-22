"""health_benefits 폴더 안에서도 사용할 수 있는 공통 실행 진입점."""
import argparse
from pathlib import Path
import runpy
import sys

COMMANDS = {
    "search": "recommendation.search_benefits",
    "collect_catalog": "collection.collect_catalog",
    "collect_many": "collection.collect_many",
    "fetch_xml": "collection.fetch_xml",
    "save_xml": "collection.save_xml",
    "create_healty_benefit": "preprocessing.create_healty_benefit",
    "backfill_audience_fields": "preprocessing.backfill_audience_fields",
    "backfill_theme_codes": "preprocessing.backfill_theme_codes",
    "backfill_application_status": "preprocessing.backfill_application_status",
    "migrate_to_benefit": "database.migrate_to_benefit",
    "verify_collection": "tests.verify_collection",
    "test_benefit_store": "tests.test_benefit_store",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.argv = [args.command, *args.args]
    runpy.run_module("health_benefits." + COMMANDS[args.command], run_name="__main__")


if __name__ == "__main__":
    main()
