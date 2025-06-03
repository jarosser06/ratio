.DEFAULT_GOAL := deploy

define cdk_deploy
	cdk deploy --require-approval never $(1)
endef

# Wipes any lingering test credentials
wipe_test_credentials:
	@echo "Wiping test credentials..."

	rm -rf test_entities

# Wipes the system by removing all entities and resetting the initialization
# state
wipe: wipe_test_credentials
	@echo "Wiping system..."

	python utils/cleanup.py

# Executes the pytest test suite
test: wipe
	@echo "Running tests..."

	pytest --disable-warnings

# Wipes local files created during deployment and testing
clean: wipe_test_credentials
	@echo "Clearning cdk.out..."

	rm -rf cdk.out

# Runs CDK Garbage Collection on the ECR repository
clean_ecr:
	@echo "Running ECR garbage collection..."

	python utils/ecr_cleanup.py

# Wraps the CDK deploy command
deploy:
	@echo "Deploying..."

	$(call cdk_deploy, --all)

deploy_process:
	@echo "Deploying Process Manager..."

	$(call cdk_deploy, -e ratio-dev-processmanagerstack)

deploy_api:
	@echo "Deploying API..."

	$(call cdk_deploy, -e ratio-dev-ratioapistack)

deploy_scheduler:
	@echo "Deploying Scheduler..."

	$(call cdk_deploy, -e ratio-dev-schedulerstack)

deploy_storage:
	@echo "Deploying Storage..."

	$(call cdk_deploy, -e ratio-dev-storagemanagerstack)

deploy_tools:
	@echo "Deploying Tools..."

	$(call cdk_deploy, -e ratio-dev-ratiobedrocktools)
	$(call cdk_deploy, -e ratio-dev-ratiocombinecontenttool)
	$(call cdk_deploy, -e ratio-dev-ratiomathtool)
	$(call cdk_deploy, -e ratio-dev-ratiorendertemplatetool)
	$(call cdk_deploy, -e ratio-dev-ratiointernalapitool)


deploy_compute: deploy_api, deploy_storage, deploy_tools, deploy_process, deploy_scheduler
