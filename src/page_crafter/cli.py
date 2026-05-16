import argparse
import os


def run_api(args: argparse.Namespace) -> None:
    """Run the FastAPI application with Uvicorn."""
    import uvicorn

    uvicorn.run(
        "page_crafter.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def run_worker(args: argparse.Namespace) -> None:
    """Run the Celery worker application."""
    from page_crafter.worker.celery_app import celery_app

    celery_app.worker_main(["worker", "--loglevel", args.loglevel])


def run_beat(args: argparse.Namespace) -> None:
    """Run the Celery Beat scheduler application."""
    from page_crafter.scheduler.celery_app import celery_app

    celery_app.worker_main(["beat", "--loglevel", args.loglevel])


def build_parser() -> argparse.ArgumentParser:
    """Build the page-crafter command line interface."""
    parser = argparse.ArgumentParser(prog="page-crafter")
    subparsers = parser.add_subparsers(dest="command", required=True)

    api = subparsers.add_parser("api", help="run the FastAPI web service")
    api.add_argument("--host", default=os.getenv("API_HOST", "0.0.0.0"))
    api.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "8000")))
    api.add_argument("--reload", action="store_true")
    api.set_defaults(func=run_api)

    worker = subparsers.add_parser("worker", help="run the Celery worker")
    worker.add_argument("--loglevel", default="info")
    worker.set_defaults(func=run_worker)

    beat = subparsers.add_parser("beat", help="run the Celery Beat scheduler")
    beat.add_argument("--loglevel", default="info")
    beat.set_defaults(func=run_beat)

    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the selected Page Crafter process."""
    args = build_parser().parse_args(argv)
    args.func(args)
