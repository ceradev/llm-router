"""Catalog benchmarks: `heuristic` (metadata → provisional) vs `live` (execution → verified).

Examples:
  python -m packages.services.benchmark.cli heuristic --model-id 1
  python -m packages.services.benchmark.cli live --model-id 1
  python -m packages.services.benchmark.cli catalog-run
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlmodel import Session

from packages.infrastructure.config.settings import get_settings
from packages.infrastructure.db.session import engine
from packages.services.benchmark.catalog_evaluation_orchestrator import (
    CatalogEvaluationConfig,
    CatalogEvaluationOrchestrator,
    catalog_evaluation_config_from_settings,
)
from packages.services.benchmark.live_model_benchmark_service import LiveModelBenchmarkService
from packages.services.benchmark.model_benchmark_service import ModelBenchmarkService

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    base_cfg = catalog_evaluation_config_from_settings(settings)
    parser = argparse.ArgumentParser(description="Catalog model benchmarks (heuristic vs live).")
    sub = parser.add_subparsers(dest="command", required=True)

    p_he = sub.add_parser("heuristic", help="Metadata screening only (max: provisional).")
    p_he.add_argument("--model-id", type=int, required=True, help="`llm_models.id`.")
    p_he.add_argument(
        "--enable-image-text-v2",
        action="store_true",
        default=base_cfg.enable_image_text_v2,
        help="Enable image->text multimodal scope in heuristic.",
    )
    p_he.add_argument(
        "--enable-file-text-v3",
        action="store_true",
        default=base_cfg.enable_file_text_v3,
        help="Enable file->text multimodal scope in heuristic.",
    )

    p_lv = sub.add_parser("live", help="OpenRouter execution benchmark (path to verified).")
    p_lv.add_argument("--model-id", type=int, required=True, help="`llm_models.id`.")
    p_lv.add_argument(
        "--enable-image-text-v2",
        action="store_true",
        default=base_cfg.enable_image_text_v2,
        help="Enable image->text multimodal scope in live benchmark.",
    )
    p_lv.add_argument(
        "--strict-image-text-checks",
        action="store_true",
        default=base_cfg.strict_image_text_checks,
        help="Use strict assertions for image->text live checks.",
    )
    p_lv.add_argument(
        "--enable-file-text-v3",
        action="store_true",
        default=base_cfg.enable_file_text_v3,
        help="Enable file->text multimodal scope in live benchmark.",
    )
    p_lv.add_argument(
        "--strict-file-text-checks",
        action="store_true",
        default=base_cfg.strict_file_text_checks,
        help="Use strict assertions for file->text live checks.",
    )

    p_cat = sub.add_parser("catalog-run", help="Batch heuristic (cataloged) then live (provisional).")
    p_cat.add_argument(
        "--max-models",
        type=int,
        default=base_cfg.max_models_per_run,
        metavar="N",
        help="Max heuristic screenings per run (default: settings).",
    )
    p_cat.add_argument(
        "--max-live",
        type=int,
        default=base_cfg.max_live_benchmarks_per_run,
        metavar="N",
        help="Max live benchmarks per run (default: settings).",
    )
    p_cat.add_argument(
        "--provider-allowlist",
        type=str,
        default=None,
        metavar="SLUGS",
        help="Comma-separated provider slugs, or omit to use CATALOG_EVALUATION_PROVIDER_ALLOWLIST / no filter.",
    )
    p_cat.add_argument(
        "--include-verified-live",
        action="store_true",
        default=base_cfg.include_verified_live,
        help="Also run live on models already verified (default: settings).",
    )
    p_cat.add_argument(
        "--delay",
        type=float,
        default=base_cfg.live_delay_seconds,
        metavar="SECONDS",
        help="Delay between live benchmarks to avoid rate limits (default: settings).",
    )
    p_cat.add_argument(
        "--enable-image-text-v2",
        action="store_true",
        default=base_cfg.enable_image_text_v2,
        help="Enable image->text multimodal scope in catalog-run.",
    )
    p_cat.add_argument(
        "--strict-image-text-checks",
        action="store_true",
        default=base_cfg.strict_image_text_checks,
        help="Use strict assertions for image->text live checks in catalog-run.",
    )
    p_cat.add_argument(
        "--enable-file-text-v3",
        action="store_true",
        default=base_cfg.enable_file_text_v3,
        help="Enable file->text multimodal scope in catalog-run.",
    )
    p_cat.add_argument(
        "--strict-file-text-checks",
        action="store_true",
        default=base_cfg.strict_file_text_checks,
        help="Use strict assertions for file->text live checks in catalog-run.",
    )

    args = parser.parse_args(argv)

    with Session(engine) as session:
        try:
            if args.command == "heuristic":
                svc = ModelBenchmarkService(session)
                out = svc.run_heuristic_screening(
                    model_id=args.model_id,
                    enable_image_text_v2=args.enable_image_text_v2,
                    enable_file_text_v3=args.enable_file_text_v3,
                )
                session.commit()
                print(
                    f"benchmark_run_id={out.benchmark_run_id} status={out.status.value} "
                    f"passed={out.passed} evaluation_status_after={out.evaluation_status_after.value}"
                )
                return 0

            if args.command == "live":
                svc = LiveModelBenchmarkService(session)
                out = svc.run_live_benchmark_for_model(
                    model_id=args.model_id,
                    enable_image_text_v2=args.enable_image_text_v2,
                    strict_image_text_checks=args.strict_image_text_checks,
                    enable_file_text_v3=args.enable_file_text_v3,
                    strict_file_text_checks=args.strict_file_text_checks,
                )
                session.commit()
                print(
                    f"benchmark_run_id={out.benchmark_run_id} status={out.status.value} "
                    f"passed={out.passed} evaluation_status_after={out.evaluation_status_after.value}"
                )
                return 0

            allow = base_cfg.provider_allowlist
            if args.provider_allowlist is not None:
                parts = {p.strip().lower() for p in args.provider_allowlist.split(",") if p.strip()}
                allow = frozenset(parts) if parts else None
            cfg = CatalogEvaluationConfig(
                max_models_per_run=max(0, args.max_models),
                max_live_benchmarks_per_run=max(0, args.max_live),
                provider_allowlist=allow,
                include_verified_live=args.include_verified_live,
                live_delay_seconds=max(0.0, args.delay),
                enable_image_text_v2=args.enable_image_text_v2,
                strict_image_text_checks=args.strict_image_text_checks,
                enable_file_text_v3=args.enable_file_text_v3,
                strict_file_text_checks=args.strict_file_text_checks,
            )
            summary = CatalogEvaluationOrchestrator(session).run(cfg)
            session.commit()
            print(
                f"catalog_eval heuristic_attempted={summary.heuristic_attempted} "
                f"heuristic_skipped_out_of_scope={summary.heuristic_skipped_out_of_scope} "
                f"heuristic_errors={summary.heuristic_errors} "
                f"live_attempted={summary.live_attempted} "
                f"live_skipped_out_of_scope={summary.live_skipped_out_of_scope} "
                f"live_errors={summary.live_errors}"
            )
            return 0
        except ValueError as exc:
            logger.error("%s", exc)
            session.rollback()
            return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
