PACKAGES := coactra lib-ai memory workspace jobs directory agent
CORE_PACKAGES := coactra memory workspace jobs agent

.PHONY: test test-core

test:
	@set -e; for package in $(PACKAGES); do printf '\n==> %s\n' "$$package"; (cd "$$package" && python3 -m pytest -q); done

test-core:
	@set -e; for package in $(CORE_PACKAGES); do printf '\n==> %s\n' "$$package"; (cd "$$package" && python3 -m pytest -q); done
