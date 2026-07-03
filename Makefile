PYTHON ?= $(shell test -x coactra/.venv/bin/python && printf '%s' "$$PWD/coactra/.venv/bin/python" || command -v python3.12 || command -v python3)
PYRIGHT ?= $(shell test -x coactra/.venv/bin/pyright && printf '%s' "$$PWD/coactra/.venv/bin/pyright" || command -v pyright || printf pyright)

.PHONY: test lint type docs compile test-examples test-base-install clean-install stale-scan live-check release-check

test:
	cd coactra && $(PYTHON) -m pytest -q -m 'not live'

lint:
	cd coactra && $(PYTHON) -m ruff check src tests

type:
	cd coactra && $(PYRIGHT)

docs:
	mkdocs build --strict

compile:
	cd coactra && $(PYTHON) -m compileall -q src/coactra

test-examples:
	cd coactra && $(PYTHON) -m pytest tests/test_examples.py -q


test-base-install:
	cd coactra && $(PYTHON) -m pytest tests/test_base_install.py -q

clean-install:
	$(PYTHON) coactra/scripts/check_clean_install.py

stale-scan:
	$(PYTHON) coactra/scripts/check_no_legacy_paths.py

live-check:
	$(PYTHON) coactra/scripts/check_live_backends.py

release-check: lint compile type test docs test-examples test-base-install clean-install stale-scan live-check
	git diff --check
