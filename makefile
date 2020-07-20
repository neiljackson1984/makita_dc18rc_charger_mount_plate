getFullyQualifiedWindowsStylePath=$(shell cygpath --windows --absolute "$(1)")
unslashedDir=$(patsubst %/,%,$(dir $(1)))
pathOfThisMakefile=$(call unslashedDir,$(lastword $(MAKEFILE_LIST)))
pathOfMakePrintableScript:=braids/makerbot_printable_maker/make_printable.py
buildFolder:=${pathOfThisMakefile}/build
sources:=$(wildcard ${pathOfThisMakefile}/*.thing)

#makerbotFiles is the list of .makerbot files that we want to ensure exist and are up to date
makerbotFiles:=$(foreach source,${sources},${buildFolder}/$(basename $(notdir ${source})).makerbot)
uploadSemaphoreFiles:=$(foreach makerbotFile,${makerbotFiles},$(makerbotFile).upload)


#the address of the makerbot to upload to
makerbotAddress:=makerbot.ad.autoscaninc.com
makerbotLinuxUsername:=root

# uploadTargets:=$(foreach source,${sources},upload_$(basename $(notdir ${source})))
makerwarePath:=C:\Program Files\MakerBot\MakerBotPrint\resources\app.asar.unpacked\node_modules\MB-support-plugin\mb_ir\MakerWare
uploadPrefix:=$(shell date +%Y%m%d_%H%M%S)--
destinationDirectoryOnTheMakerbot:=/home/usb_storage/
# miraclegrueConfigFile=miracle_config.hjson
# miraclegrueConfigFile=default_miraclegrue_config.json
miraclegrueConfigFile=default+baseLayer=none_miraclegrue_config.json
# miraclegrueConfigOverridesFile=miracle_config_overrides.hjson
miraclegrueConfigTransformFile=miraclegrue_config_transform.py
# miraclegrueConfigFile:=default_miracle_config.json
venv:=$(shell cd "$(abspath $(dir ${pathOfMakePrintableScript}))" > /dev/null 2>&1; pipenv --venv || echo initializeVenv)
# the variable 'venv' will evaluate to the path of the venv, if it exists, or else will evaluate to 'initializeVenv', which is a target that we have created below.
# in either case, we want to use venv as a prerequisite for default.

.PHONY: initializeVenv

.PHONY: default
default: $(makerbotFiles) $(uploadSemaphoreFiles)


# ${buildFolder}/%.makerbot: ${pathOfThisMakefile}/%.thing ${pathOfMakePrintableScript} | ${buildFolder} ${venv} 
	# @echo "====== BUILDING $@ from $< ======= "
	# cd "$(abspath $(dir ${pathOfMakePrintableScript}))" > /dev/null 2>&1; \
	# pipenv run python \
		# "$(call getFullyQualifiedWindowsStylePath,${pathOfMakePrintableScript})" \
		# --makerware_path="${makerwarePath}" \
		# --input_model_file="$(call getFullyQualifiedWindowsStylePath,$<)" \
		# --input_miraclegrue_config_file="$(call getFullyQualifiedWindowsStylePath,${miraclegrueConfigFile})" \
		# --output_annotated_miraclegrue_config_file="$(call getFullyQualifiedWindowsStylePath,${buildFolder}/miracle_config_annotated.hjson)" \
		# --output_makerbot_file="$(call getFullyQualifiedWindowsStylePath,$@)" \
		# --output_gcode_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).gcode)" \
		# --output_json_toolpath_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).jsontoolpath)" \
		# --output_metadata_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).meta.json)"

${buildFolder}/%.makerbot: ${pathOfThisMakefile}/%.thing ${pathOfMakePrintableScript} ${miraclegrueConfigFile} ${miraclegrueConfigTransformFile} | ${buildFolder} ${venv} 
	@echo "====== BUILDING $@ from $< ======= "
	cd "$(abspath $(dir ${pathOfMakePrintableScript}))" > /dev/null 2>&1; \
	pipenv run python \
		"$(call getFullyQualifiedWindowsStylePath,${pathOfMakePrintableScript})" \
		--makerware_path="${makerwarePath}" \
		--input_model_file="$(call getFullyQualifiedWindowsStylePath,$<)" \
		--input_miraclegrue_config_file="$(call getFullyQualifiedWindowsStylePath,${miraclegrueConfigFile})" \
		--input_miraclegrue_config_transform_file="$(call getFullyQualifiedWindowsStylePath,${miraclegrueConfigTransformFile})" \
		--output_annotated_miraclegrue_config_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).miraclegrue_config_annotated.hjson)" \
		--output_makerbot_file="$(call getFullyQualifiedWindowsStylePath,$@)" \
		--output_gcode_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).gcode)" \
		--output_metadata_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).meta.json)" \
		--output_miraclegrue_config_diff_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).miraclegrue_config_diff)" \
		--output_miraclegrue_log_file="$(call getFullyQualifiedWindowsStylePath,$(dir $@)$(basename $(notdir $@)).miraclegrue_log)" \
	

${buildFolder}/%.upload: ${buildFolder}/%
	@echo "====== UPLOADING $< TO $(makerbotLinuxUsername)@$(makerbotAddress):${destinationDirectoryOnTheMakerbot}${uploadPrefix}$(notdir $<) ======= "
	pscp "$(call getFullyQualifiedWindowsStylePath,$<)" "$(makerbotLinuxUsername)@$(makerbotAddress):${destinationDirectoryOnTheMakerbot}${uploadPrefix}$(notdir $<)"
	touch "$@"
	
# .PHONY: upload
## # upload: $(foreach source,${sources},upload_$(basename $(notdir ${source})))
## upload: $(makerbotFiles)
## 	#TO DO: for each makerbotFile in makerbotFiles: upload makerbotFile
## 	
## # upload_%: ${buildFolder}/%.makerbot
## 	# pscp "$(call getFullyQualifiedWindowsStylePath,$<)" "$(makerbotLinuxUsername)@$(makerbotAddress):${destinationDirectoryOnTheMakerbot}${uploadPrefix}$(notdir $<)"

${buildFolder}:
	@echo "====== CREATING THE BUILD FOLDER ======="
	@echo "buildFolder: ${buildFolder}"
	mkdir --parents "${buildFolder}"
#buildFolder, when included as a prerequisite for rules, should be declared as an order-only prerequisites (by placing it to the right of a "|" character in the 
# list of prerequisites.  See https://www.gnu.org/software/make/manual/html_node/Prerequisite-Types.html 


# ${venv}: 
# ${venv}: $(dir ${pathOfMakePrintableScript})Pipfile $(dir ${pathOfMakePrintableScript})Pipfile.lock
${venv}: $(dir ${pathOfMakePrintableScript})Pipfile $(dir ${pathOfMakePrintableScript})Pipfile.lock
	@echo "====== INITIALIZING VIRTUAL ENVIRONMENT ======= "
	# @echo "venv: ${venv}"
	@echo "target: $@"
	# # @echo "prerequisites: $^"
	# @echo "prerequisites that are newer than the target: $?"
	# # @echo "prerequisites that are not newer than the target: $^ - $?"
	# @echo "prerequisites that are not newer than the target: $(filter-out $?,$^)"
	# @echo "order-only prerequisites: $|"
	cd "$(abspath $(dir ${pathOfMakePrintableScript}))"; pipenv install
	touch $(shell cd "$(abspath $(dir ${pathOfMakePrintableScript}))" > /dev/null 2>&1; pipenv --venv)

.SILENT:		


# SHELL=sh	
	