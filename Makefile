.PHONY: post-create init sync

post-create: init sync

init:
	@echo "\nInitializing Python environment..."
	@(uv python install ${PYTHON_VERSION} && \
	if [ ! -f pyproject.toml ]; then \
		if [ "${UV_INIT_BARE}" = "true" ]; then \
			uv init --bare --python ${PYTHON_VERSION}; \
		else \
			uv init --python ${PYTHON_VERSION}; \
		fi; \
	fi) > /tmp/init.log 2>&1
	@echo "✓ Initialization complete (log: /tmp/init.log)\n"

sync:
	@echo "Syncing dependencies..."
	@uv sync > /tmp/uv-sync.log 2>&1
	@echo "✓ Dependency sync complete (log: /tmp/uv-sync.log)\n"

lint:
	@uv run ruff check ./src

format:
	@uv run ruff format ./src

freeze:
	@echo "Freezing dependencies..."
	@echo "# Generated on $$(date)" > /tmp/requirements.txt
	@uv pip freeze >> /tmp/requirements.txt
	@echo "✓ Dependencies frozen (log: /tmp/requirements.txt)"
