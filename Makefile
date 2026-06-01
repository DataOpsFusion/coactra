PACKAGES := lib-ai memory workspace workflow organization agent

.PHONY: test
test:
	@set -e; for package in $(PACKAGES); do printf '\n==> %s\n' "$$package"; (cd "$$package" && python3 -m pytest -q); done
