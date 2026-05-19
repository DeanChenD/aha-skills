PYTHON ?= python3

.PHONY: test idea dao tip todo help

help:
	@echo "make test   - run full pytest suite"
	@echo "make idea   - run idea CLI (pass args via ARGS=...)"
	@echo "make dao    - run dao CLI"
	@echo "make tip    - run tip CLI"
	@echo "make todo   - run todo CLI"

test:
	$(PYTHON) scripts/run_tests.py

idea:
	$(PYTHON) skills/idea/scripts/idea.py $(ARGS)

dao:
	$(PYTHON) skills/dao/scripts/dao.py $(ARGS)

tip:
	$(PYTHON) skills/tip/scripts/tip.py $(ARGS)

todo:
	$(PYTHON) skills/todo/scripts/todo.py $(ARGS)
