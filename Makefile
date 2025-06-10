.DEFAULT_GOAL := deploy

define cdk_deploy
	cdk deploy --require-approval never $(1)
endef

# Wipes the system by removing all entities and resetting the initialization
# state
wipe:
	@echo "Wiping system..."

	python utils/cleanup.py

# Executes the pytest test suite
test: wipe
	@echo "Running tests..."

	pytest --disable-warnings

# Wipes local files created during deployment and testing
clean:
	@echo "Clearning cdk.out..."

	rm -f deploy.log
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

deploy_auth:
	@echo "Deploying Auth..."

	$(call cdk_deploy, -e ratio-dev-authstack)

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


deploy_compute: deploy_auth deploy_storage deploy_process deploy_scheduler deploy_tools 
