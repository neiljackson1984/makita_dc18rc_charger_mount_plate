buildPath=build
getFullyQualifiedWindowsStylePath=$(shell cygpath --windows --absolute "$(1)")
pathOfMakePrintableScript=braids/makerbot_printable_maker/make_printable.py

default:
	mkdir -p ${buildPath}
	cd "$(abspath $(dir ${pathOfMakePrintableScript}))"; \
	pipenv run python \
		"$(call getFullyQualifiedWindowsStylePath,${pathOfMakePrintableScript})" \
		--makerware_path="C:\Program Files\MakerBot\MakerBotPrint\resources\app.asar.unpacked\node_modules\MB-support-plugin\mb_ir\MakerWare" \
		--input_file="$(call getFullyQualifiedWindowsStylePath,bit_holder.thing)" \
		--output_file="$(call getFullyQualifiedWindowsStylePath,${buildPath}/bit_holder.makerbot)" \
		--miraclegrue_config_file="$(call getFullyQualifiedWindowsStylePath,miracle_config.json)"


.SILENT:		