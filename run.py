"""CLI entry point for Healthcare Revenue Cycle Intelligence."""

from __future__ import annotations

import argparse
import uvicorn

from src.ba_artifacts import generate_all_ba_artifacts
from src.pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Healthcare Revenue Cycle Intelligence ETL & Dashboard Runner"
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Run ETL pipeline and generate BA workbooks/PDF without launching web server.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    counts = run_pipeline()
    print("ETL completed:", counts)
    generate_all_ba_artifacts()
    print("Business Analysis workbooks and PDF report generated.")

    if not args.build_only:
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
