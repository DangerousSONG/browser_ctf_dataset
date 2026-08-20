.PHONY: generate validate sync mcp bootstrap wrap help

CVE ?= CVE-2024-5830
BENCH := third_party/exploitbench/benchmarks/bench-v8

# Default: unify formats. Does not compile V8.
generate:
	python scripts/generate_all.py
	python scripts/validate_all.py

validate:
	python scripts/validate_all.py

sync:
	python scripts/sync_upstream.py

mcp: sync
	$(MAKE) -C $(BENCH)/mcp-server all

bootstrap:
	python scripts/bootstrap_bug.py $(CVE)

wrap:
	python scripts/wrap_harbor_task.py $(CVE) --force

# Optional. Linux amd64, ~60min, ~70GB. Not required to submit the task package.
build-inner:
	python scripts/build_inner.py $(CVE)

help:
	@echo "Submit path: unify Harbor packages (make generate). No V8 compile."
	@echo "Fill real Dockerfile commits: make sync && make mcp && make bootstrap CVE=$(CVE)"
	@echo "Someone else's builder: make build-inner CVE=$(CVE)"
