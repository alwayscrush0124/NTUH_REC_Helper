.PHONY: help setup check generate online attachments pdf templates onboard validate all dashboard checklist test lint format clean init \
        doctor build \
        set-phase new amendment continuing closure suspension sae deviation other import

# Thin wrapper over the `rech` CLI (rec_helper/cli.py) for working in this checkout.
# Outside the repo, install the package and call `rech` directly (see README).
# Single source of truth: config.toml (+ the files it references, e.g. cv.toml, 中文計畫摘要.md)
CONFIG  := config.toml
OUTPUT  := output
# No uv? `make all RUN="python -m"` uses the current Python (rech → python -m rec_helper).
RUN     ?= uv run
RECH    := $(if $(filter python%,$(RUN)),$(RUN) rec_helper,$(RUN) rech)
# Override the phase for one run without editing config.toml: make all PHASE=closure
PHASE   ?=
export PHASE

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@printf "  \033[36m%-12s\033[0m %s\n" "<phase>" "make closure|amendment|continuing|… = make all PHASE=<phase>"

setup: ## Install dependencies
	uv sync

init: ## Start from the example: make init EXAMPLE=ntuh-chart-review (refuses to overwrite)
	$(RECH) init $(or $(EXAMPLE),ntuh-chart-review) $(if $(FORCE),--force)

check: ## Resolve @references in config.toml and validate required fields
	$(RECH) check $(CONFIG)

generate: ## Generate DOCX attachments from config.toml
	$(RECH) generate $(CONFIG) --output $(OUTPUT)

online: ## e-REC copy-paste sheets; SKELETON=1 writes 線上填寫.md
	$(RECH) online $(CONFIG) --output $(OUTPUT) $(if $(SKELETON),--skeleton)

attachments: ## Questions of the row-filled attachments; SKELETON=1 appends them to 附件填寫.md
	$(RECH) attachments $(CONFIG) $(if $(SKELETON),--skeleton)

pdf: ## Convert DOCX → PDF + PNG previews
	$(RECH) pdf --output $(OUTPUT)

templates: ## Download the committee's official blank forms into templates/
	$(RECH) templates $(CONFIG)

onboard: ## Draft a new institution from blanks in templates/$(INST)/  (make onboard INST=myhosp)
	@test -n "$(INST)" || (echo "usage: make onboard INST=<id>  (blanks in templates/<id>/)"; exit 2)
	$(RECH) onboard $(INST)

validate: ## Layout/font safety gate vs the official blank forms
	$(RECH) validate $(CONFIG) --output $(OUTPUT)

all: ## Generate + online sheets + PDF + validate + dashboard
	$(RECH) all $(CONFIG) --output $(OUTPUT)

dashboard: ## Show submission status
	$(RECH) dashboard $(CONFIG) --output $(OUTPUT)

checklist: ## View checklist
	@cat checklist.md

test: ## Run tests
	$(RUN) pytest -v

doctor: ## Check LibreOffice, poppler, form font, config and cached blanks
	$(RECH) doctor $(CONFIG)

build: ## Build the sdist + wheel into dist/
	uv build

lint: ## Lint Python sources
	$(RUN) ruff check .

format: ## Auto-fix lint issues (imports, etc.)
	$(RUN) ruff check --fix .

clean: ## Remove generated files
	rm -rf $(OUTPUT) checklist.md

set-phase: ## Persist the phase in config.toml (keeps comments): make set-phase PHASE=closure
	@test -n "$(PHASE)" || { echo "Usage: make set-phase PHASE=<phase>"; exit 1; }
	$(RECH) set-phase $(PHASE) $(CONFIG)

# Phase shortcuts: make closure == make all PHASE=closure (config.toml untouched)
new amendment continuing closure suspension sae deviation other import:
	@$(MAKE) --no-print-directory all PHASE=$@
