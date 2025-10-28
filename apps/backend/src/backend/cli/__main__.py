"""Allow `python -m backend.cli` to invoke the command-line entrypoint."""

from .main import main


if __name__ == "__main__":
    main()
