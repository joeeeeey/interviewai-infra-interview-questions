.PHONY: help makrodnw q1 q2 q3 next reset self-attempt smoke

help:
	@echo "Targets:"
	@echo "  make makrodnw          # show next question"
	@echo "  make makrodnw STEP=2   # show specific step"
	@echo "  make q1 | q2 | q3"
	@echo "  make next              # alias of makrodnw"
	@echo "  make reset             # reset candidate progress"
	@echo "  make self-attempt      # run local candidate attempt and generate artifact"
	@echo "  make smoke             # only credential + API smoke test"

makrodnw:
	@./scripts/show_question.sh $(if $(STEP),$(STEP),next)

q1:
	@./scripts/show_question.sh 1

q2:
	@./scripts/show_question.sh 2

q3:
	@./scripts/show_question.sh 3

next: makrodnw

reset:
	@./scripts/show_question.sh reset

self-attempt:
	@./scripts/self_attempt.py --cred-file tmp-cred.md --out-dir artifacts

smoke:
	@./scripts/self_attempt.py --cred-file tmp-cred.md --out-dir artifacts --smoke-only
