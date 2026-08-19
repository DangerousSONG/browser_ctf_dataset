.PHONY: all validate build verify clean

# 默认：验证所有靶场
all: validate

# 验证所有 CVE 目录
validate:
	@python3 scripts/validate_all.py

# 构建所有镜像
build:
	@python3 scripts/build_all.py

# 验证单个靶场
verify:
	@if [ -z "$(CVE)" ]; then \
		echo "Usage: make verify CVE=cve-2018-17463"; \
		exit 1; \
	fi
	@cd $(CVE) && bash run-tests.sh

# 清理所有镜像
clean:
	@docker images -q "browser-ctf/*" | xargs -r docker rmi -f 2>/dev/null || true
