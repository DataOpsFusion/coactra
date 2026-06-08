.PHONY: test lint type docs compile test-examples test-base-install clean-install stale-scan live-check release-check

test:
	cd coactra && python3 -m pytest -q -m 'not live'

lint:
	cd coactra && python3 -m ruff check src tests

type:
	cd coactra && python3 -m pyright

docs:
	mkdocs build --strict

compile:
	cd coactra && python3 -m compileall -q src/coactra

test-examples:
	cd coactra && python3 -m pytest tests/test_examples.py -q


test-base-install:
	cd coactra && python3 -m pytest tests/test_base_install.py -q

clean-install:
	python3 coactra/scripts/check_clean_install.py

stale-scan:
	python3 coactra/scripts/check_no_legacy_paths.py

live-check:
	python3 coactra/scripts/check_live_backends.py

release-check: lint compile test docs test-examples test-base-install clean-install stale-scan live-check
	git diff --check
