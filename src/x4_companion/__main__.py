def main() -> int:
    from .app import main as app_main
    return app_main()

if __name__ == "__main__":
    import sys
    sys.exit(main())
