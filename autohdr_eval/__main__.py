import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


def _main() -> int:
    from autohdr_eval.cli import main

    return main()


raise SystemExit(_main())
