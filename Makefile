.PHONY: local-up local-down local-env-check local-infra-plan local-infra-apply local-sam-build local-sam-deploy local-lambda-deploy local-seed local-smoke-test local-status local-logs local-install-autostart local-uninstall-autostart local-restart

local-up:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-up

local-down:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-down

local-env-check:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-env-check

local-infra-plan:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command infra-plan

local-infra-apply:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command infra-apply

local-sam-build:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command sam-build

local-sam-deploy:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command sam-deploy

local-lambda-deploy:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command lambda-deploy

local-seed:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-seed

local-smoke-test:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-smoke-test

local-status:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-status

local-logs:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-logs

local-install-autostart:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-install-autostart

local-uninstall-autostart:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-uninstall-autostart

local-restart:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-restart
