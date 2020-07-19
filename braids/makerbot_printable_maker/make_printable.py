import argparse
import os
import re
import json
import pathlib
import sys
import math
import copy
# import numpy
import subprocess
import hjson #see https://hjson.github.io/hjson-py/
import tempfile
import datetime
import progress
import progress.bar
import jsondiff
import jsondiff_by_makerbot
# import importlib.util
import shutil


# This progress bar library is deficient in that it does not make any effort to output any sort of progress indicator in the case where the 
# terminal is not a tty (i.e. in the case where the terminal does not support terminal control codes)
# As a hack, I have simply disable the tty checkinbg so that terminal control codes are blindly emitted, whither the terminal supports them or not.
# but this is not ideal because in terminals that do not support control codes, we see the literal control codes, which look like gobbledygook.
class MyProgressBar(progress.bar.Bar):
    check_tty = False
    hide_cursor = False
    suffix='%(percent)d%% - %(elapsed_td)s/%(estimatedTotalDuration_td)s'
    @property
    def estimatedTotalDuration(self):
        try:
            return int(math.ceil(1/self.progress * self.elapsed))
        except ZeroDivisionError:
            return 0
    @property
    def estimatedTotalDuration_td(self):
        return datetime.timedelta(seconds=self.estimatedTotalDuration)
    
    def setProgress(self, newValue):
        self.index = newValue * self.max

    def setProgressAndUpdate(self, newValue):
        self.setProgress(newValue)
        self.update()

    # overriding the original clearln() definition so as not to emit control codes.
    def clearln(self): 
        if self.file and self.is_tty():
            # print('\r\x1b[K', end='', file=self.file)
            print('\r', end='', file=self.file)









 






parser = argparse.ArgumentParser(description="Generate a .makerbot toolpath file from a .thing file and a mircale_grue configuration file.")
parser.add_argument("--makerware_path", action='store', nargs=1, required=True, 
    help=
        "the path of the MakerWare folder, which comes with Makerbot Print.  Typically, on a " 
        + "Windows machine, the MakerWare path is " 
        + "\"" 
        + "C:\\Program Files\\MakerBot\\MakerBotPrint\\resources\\app.asar.unpacked\\node_modules\\MB-support-plugin\\mb_ir\\MakerWare"
        + "\""
        + "."
)
parser.add_argument("--input_model_file", action='store', nargs=1, required=True, help="the .thing file to be sliced.")
parser.add_argument("--input_miraclegrue_config_file", action='store', nargs=1, required=True, help="The miraclegrue config file.  This may be either a plain old .json file, or an hjson file, which is json with more relaxed syntax, and allows comments.")
# parser.add_argument("--input_miraclegrue_config_overrides_file", action='store', nargs=1, required=False, help="This is a file of the same structure as the miracle_grue_config_file.  We will construct the configuration that we pass to miracle_grue " 
#     + " and then applying any values that may be specified in input_miraclegrue_config_overrides_file.")
parser.add_argument("--input_miraclegrue_config_transform_file", action='store', nargs=1, required=False, 
    help="is expected to contain valid python code that defines a function "
        + "named \"transformMiraclegrueConfig\", which is expected to take a single argument, a dict, which is the configuration "
        + "that is to be transformed.  transformMiraclegrueConfig can modify the configuration as it sees fit."
)
parser.add_argument("--output_annotated_miraclegrue_config_file", action='store', nargs=1, required=False, help="An hjson file to be created by inserting the descriptions from the schema, as comments, interspersed within the miracle_grue_config json entries.")
parser.add_argument("--output_miraclegrue_config_diff_file", action='store', nargs=1, required=False, help="a report showing the difference between the config after applying the transform compared with the input config file.")
parser.add_argument("--output_makerbot_file", action='store', nargs=1, required=False, help="the .makerbot file to be created.")
parser.add_argument("--output_gcode_file", action='store', nargs=1, required=False, help="the .gcode file to be created.")
parser.add_argument("--output_previewable_gcode_file", action='store', nargs=1, required=False, help="A gcode file that we will create by taking the gcode produced by miracle_grue and modifying it to produce a gcode file sutiable for previeiwing in the Cura slicer.")
parser.add_argument("--output_json_toolpath_file", action='store', nargs=1, required=False, help="the .jsontoolpath file to be created.")
parser.add_argument("--output_metadata_file", action='store', nargs=1, required=False, help="the .json metadata file to be created.")
parser.add_argument("--output_miraclegrue_log_file", action='store', nargs=1, required=False, help="an output file to which to write the miraclegrue log.")




args, unknownArgs = parser.parse_known_args()

#resolve all of the paths passed as arguments to fully qualified paths:
input_model_file_path = pathlib.Path(args.input_model_file[0]).resolve()
output_makerbot_file_path = (pathlib.Path(args.output_makerbot_file[0]).resolve() if args.output_makerbot_file else None)
output_gcode_file_path = (pathlib.Path(args.output_gcode_file[0]).resolve() if args.output_gcode_file else None)
output_previewable_gcode_file_path = (pathlib.Path(args.output_previewable_gcode_file[0]).resolve() if args.output_previewable_gcode_file else None)
output_json_toolpath_file_path = (pathlib.Path(args.output_json_toolpath_file[0]).resolve() if args.output_json_toolpath_file else None)
output_metadata_file_path = (pathlib.Path(args.output_metadata_file[0]).resolve() if args.output_metadata_file else None)
# input_miraclegrue_config_overrides_file_path = (pathlib.Path(args.input_miraclegrue_config_overrides_file[0]).resolve() if args.input_miraclegrue_config_overrides_file else None)
input_miraclegrue_config_transform_file_path = (pathlib.Path(args.input_miraclegrue_config_transform_file[0]).resolve() if args.input_miraclegrue_config_transform_file else None)
output_miraclegrue_config_diff_file_path = (pathlib.Path(args.output_miraclegrue_config_diff_file[0]).resolve() if args.output_miraclegrue_config_diff_file else None)
output_miraclegrue_log_file_path = (pathlib.Path(args.output_miraclegrue_log_file[0]).resolve() if args.output_miraclegrue_log_file else None)


makerware_path = pathlib.Path(args.makerware_path[0]).resolve()
input_miraclegrue_config_file_path = pathlib.Path(args.input_miraclegrue_config_file[0]).resolve()



#the path of the python executable included with makerware:
makerware_python_executable_path = makerware_path.joinpath("python3.4.exe").resolve()
makerware_python_working_directory_path = makerware_path.joinpath("python34").resolve()
miraclegrue_executable_path = makerware_path.joinpath("miracle_grue.exe").resolve()

# sliceLibraryEggPath = list(makerware_path.joinpath("python").glob("slice_library*.egg"))[0]

# print("sliceLibraryEggPath.resolve(): " + str(sliceLibraryEggPath.resolve()))		# sliceLibraryEggPath.resolve()

# # spec = importlib.util.spec_from_file_location('slice_library', sliceLibraryEggPath.resolve())
# # module = importlib.util.module_from_spec(spec)
# # sys.modules['slice_library'] = module
# # spec.loader.exec_module(module)

# sys.path.insert(0, str(sliceLibraryEggPath.resolve()))
# # This is how sliceconfig finds its resource files
# os.environ['MB_RESOURCE_PATH'] = str(makerware_path)
# import slice_library.tinything_processor

# print("dir(slice_library): " + str(dir(slice_library)))		# dir(slice_library)
# print("dir(slice_library.tinything_processor): " + str(dir(slice_library.tinything_processor)))		# dir(slice_library.tinything_processor)

#the path of the makerware sliceconfig python script:
makerware_sliceconfig_path = makerware_path.joinpath("sliceconfig").resolve()

miraclegrueConfig = hjson.load(open(input_miraclegrue_config_file_path ,'r'))

if input_miraclegrue_config_transform_file_path:
    #modify miraclegrueConfig by applying any overrides that may be specified in input_miraclegrue_config_overrides_file
    #miraclegrueConfigOverrides = hjson.load(open(input_miraclegrue_config_overrides_file_path ,'r'))
    # print("miraclegrueConfigOverrides: " + str(type(miraclegrueConfigOverrides)))

    # record the initia; state of miracleGrueConfig, before we allow the transform to (possibly) modify it.
    # We do this so that we can, if the user has requested a output_miraclegrue_config_diff_file, generate
    # a report showing the differences between miraclegrueConfig before and after the transform operates on it.
    initialMiraclegrueConfig = copy.deepcopy(miraclegrueConfig)

    #input_miraclegrue_config_overrides_file is expected to contain valid python code that defines a function
    # named "transformMiraclegrueConfig", which is expected to take a single argument, a dict, which is the configuration
    # that is to be transformed.  transformMiraclegrueConfig can modify the configuration as it sees fit.
    # Should we expect transformMiraclegrueConfig() to return a dict, that we will then take to be the new miraclegrueConfig,
    # or, alternatively, should we expect to transformMiraclegrueConfig() to modify the dict that is passed to it?  -- I am still deciding.
    # It seems like the return value approach would be the most flexible.

    isolatedGlobals = dict()

    exec(open(input_miraclegrue_config_transform_file_path, 'r').read(), isolatedGlobals)
    #I think, although am not entirely certain, that passing the isolatedGlobals object prevents the code in input_miraclegrue_config_transform_file_path
    # from being able to muck with, or even see, our globals here.  This mechanism does not prevent the execution of arbitrary code and so is certainly not suitable for a production application.
    # We ought to figure out how to run transformMiraclegrueConfig in a sandbox.

    # print("isolatedGlobals.keys(): " + str(isolatedGlobals.keys()))
    # print("type(isolatedGlobals[\"transformMiraclegrueConfig\"]): " + str(type(isolatedGlobals["transformMiraclegrueConfig"])))		#     type(isolatedGlobals["transformMiraclegrueConfig"])

    miraclegrueConfig = isolatedGlobals["transformMiraclegrueConfig"](miraclegrueConfig)
    # print("miraclegrueConfig['foo']: " + str(miraclegrueConfig['foo']))		#     miracleGrueConfig['foo']



    if output_miraclegrue_config_diff_file_path:
        # diff = jsondiff.diff(initialMiraclegrueConfig, miraclegrueConfig)
        # print("diff.keys(): " + str(diff.keys()))		#         diff.keys()
        # open(output_miraclegrue_config_diff_file_path ,'w').write(str(diff))

        diff = jsondiff_by_makerbot.JSONDiff(initialMiraclegrueConfig, miraclegrueConfig)
        open(output_miraclegrue_config_diff_file_path ,'w').write(str(diff.pretty_str(trim_size=300)))
  


def tabbedWrite(file, content, tabLevel=0, tabString="    ", linePrefix=""):
    file.write(
        "\n".join(
            map( 
                lambda y: tabString*tabLevel + linePrefix + y,
                str(content).splitlines()
            )
        ) + "\n"
    )

def prefixAllLines(x, prefix):
    return "\n".join(
        map( 
            lambda y: prefix + y,
            str(x).splitlines()
        )
    )

def indentAllLines(x, indentString="    "):
    return prefixAllLines(x, indentString)

def makeBlockComment(x):
    lines = str(x).splitlines()  
    return "\n".join(
        ["/* " + lines[0]]
        + list(
            map(
                lambda y: " * " + y,
                lines[1:]
            )
        )
        + [" */"]
    )

def addParentheticalRemarkAtEndOfFirstLine(x, remark=None): 
    lines = str(x).splitlines()
    return "\n".join(
        [lines[0] + (" (" + str(remark) + ")" if remark else "")]
        + lines[1:]
    )



# path is expected to be a list (of keys)
def getSchemedTypeName(path, schema):
    if len(path) == 0:
        return '__top__'
    schemedTypeOfParent = getSchemedType(path[:-1],schema)
    if schemedTypeOfParent:
        if schemedTypeOfParent['mode'] == "aggregate":
            memberSpec = (
                    list(
                        filter(
                            lambda x: x['id'] == path[-1],
                            schemedTypeOfParent["members"]
                        )
                    ) or [None]
                )[0]
            if memberSpec:
                return memberSpec['type']
        elif schemedTypeOfParent['json_type'] == "object":
            return schemedTypeOfParent['value_type']
        elif schemedTypeOfParent['json_type'] == "array":
            return schemedTypeOfParent['element_type']
    return None

def getSchemedType(path, schema):
    # print("getSchemedType() was called with path " + str(path))
    schemedTypeName = getSchemedTypeName(path, schema)
    if schemedTypeName:
        return schema.get(schemedTypeName)
    return None

def getMemberIds(schemedType):
    return (
        map(
            lambda x: x['id'],
            schemedType['members']
        )
        if (schemedType and schemedType.get('mode') == "aggregate" )
        else None
    )


#returns the annotation text that is to appear immediately
# before the entry having the specified path.
def getAnnotationForEntry(path, schema):
    schemedTypeOfParent = getSchemedType(path[:-1],schema)
    if schemedTypeOfParent and schemedTypeOfParent['mode'] == "aggregate":
        memberSpec = (
                list(
                    filter(
                        lambda x: x['id'] == path[-1],
                        schemedTypeOfParent["members"]
                    )
                ) or [None]
            )[0]
        if memberSpec:
            return "\n".join(
                [path[-1]]
                + (["name: " + memberSpec.get('name')] if (memberSpec.get('name') and (memberSpec.get('name') != path[-1])) else [])
                + list(
                    map(
                        lambda k: k + ": " + hjson.dumps(memberSpec[k]),
                        filter(
                            lambda k: k not in ['id','name'],
                            memberSpec.keys()
                        )
                    )
                )   
            )
        else:
            return "THIS ELEMENT IS NOT SPECIFIED IN THE SCHEMA."
    else:
        return None

#entryFormat shall be a streing that is either "dictEntry" or "listEntry"
# def dumpsAnnotatedHjsonEntry(value, path, schema, entryFormat):
#     # print("dumpsAnnotatedHjsonEntry was called with path: " + str(path))
#     entry = (str(path[-1]) + ": "  if entryFormat == "dictEntry" else "") + dumpsAnnotatedHjsonValue(value, path, schema)
#     annotation = getAnnotationForEntry(path, schema)
#     return ("\n" + prefixAllLines(annotation, "// ") + "\n" if annotation else "") + entry


def dumpsAnnotatedHjsonValue(value, path, schema):
    # print("now working on path: " + str(path))
    returnValue=""
    schemedType = getSchemedType(path, schema)
    
    isIterable = (
        isinstance(value, dict)
        or isinstance(value, list)
        or (schemedType and schemedType.get('mode') == "aggregate" )
        or (schemedType and schemedType.get('json_type') == "object") 
        or (schemedType and schemedType.get('json_type') == "array" )
    )
    if isIterable:
        if isinstance(value, dict):
            braces=["{","}"]
            keysInValue=set(value.keys())
            keysInSchema=set(getMemberIds(schemedType) or [])
            subentryFormat="dictEntry"
        else:
            braces=["[","]"]
            keysInValue=set(range(len(value)))
            keysInSchema=set([])
            subentryFormat="listEntry"
        returnValue += braces[0] + "\n"
        for key in sorted(list(keysInValue.union(keysInSchema))):
            annotation = getAnnotationForEntry(path + [key], schema)
            
            if key in keysInValue:
                subValue = value[key]
                entry = (key + ": "  if subentryFormat == "dictEntry" else "") + dumpsAnnotatedHjsonValue(subValue, path + [key], schema)
            else:
                subValue = None
                entry = "// VALUE NOT SPECIFIED"
            
            returnValue += indentAllLines(
                (
                    "\n" + makeBlockComment(annotation) + "\n" 
                    if annotation else ""
                ) 
                + entry
            ) + "\n"
        returnValue += braces[1] + "\n"
    else:
        returnValue += hjson.dumps(value) + "\n"
    return returnValue    

#inputFile is a readable file-like object that is assumed to be a valid jsontoolpath file
#outputGcodeFile is a writeable file-like object that is assumed to be the destination where we want to dump the gcode
#progressReportingCallback, if given, is expected to be a function that will be passed a single argument:
# a float representing the completion ratio.
def generatePreviewableGcode(inputJsontoolpathFile, outputGcodeFile, progressReportingCallback = None):
    # print("generating previewable gcode")
    # read the jsontoolpath into memory (might it be better to do this in a way that does not require us to read the entire file into memory at once?)
    toolpath = json.load(inputJsontoolpathFile)
    noodleType = None
    layerNumber = 0
    lastUpperPosition = None
    allTags: set = set()
    # allFunctions: set = set()
    
    for index in range(len(toolpath)):
        # print("now working on item " + str(index))
        item = toolpath[index]
        command = item.get('command')
        if command:
            function = command['function']
            # allFunctions.add(function)
            if function == 'move':
                # look at tags to figure out whether we need to emit a ";TYPE:..." line
                tags = set(command['tags'])
                allTags.update(tags)

                # tags encountered in a typical jsontoolpath:
                #   BeadMode External
                #   BeadMode Internal
                #   BeadMode Internal Thick
                #   BeadMode User3
                #   Connection
                #   Infill
                #   Inset
                #   Invalid Move
                #   Leaky Travel Move
                #   Long Restart
                #   Restart
                #   Retract
                #   Support
                #   Trailing Extrusion Move
                #   Travel Move

                # we need to map these (or, more accurately, combinations of these tags) to 
                # one of the following values for noodleType:
                # The travel and retract moves are detected implicitly by the cura gcode previewer, so they 
                # don't have an explicit noodleType (which is one of the reasons I chose the name "noodleType":
                # these categroies only apply to moves that produce a noodle.
                #
                #    WALL-INNER         
                #    WALL-OUTER         
                #    SKIN               
                #    SKIRT              
                #    SUPPORT            
                #    FILL              
                #    SUPPORT-INTERFACE  
                #    PRIME-TOWER        



                if "Support" in tags:
                    thisNoodleType = "SUPPORT"
                elif "Infill" in tags:
                    thisNoodleType = "FILL"
                elif "Inset" in tags:
                    #there are two possible senses for the words inner/internal and outer/external.  On the one hand, we might be
                    #  trying to distinguish between faces of holes vs. "outer" faces.  On the other hand, we might be
                    #  referring to the outermost shell vs. inner shells.
                    # I am not entirely sure if Cura's concept of WALL-OUTER vs. WALL-INNER is the same as MAkerbot's concept of BeadMode External
                    
                    tagsContainingExternal = (tag for tag in tags if "External" in tag)
                    tagsContainingInternal = (tag for tag in tags if "Internal" in tag)
                    # print("\n" + str(len(list(tagsContainingExternal)))  + "\t" + str(len(list(tagsContainingInternal))) + "\n")
                    if tagsContainingExternal:
                        thisNoodleType = "WALL-OUTER"
                    elif tagsContainingInternal:
                        thisNoodleType = "WALL-INNER"
                    else:
                        print(
                            "strangely, at index " + str(index) + " in the json toolpath, we have encountered a \"move\" "
                            + "command having the \"Inset\" tag where none of the tags contains the word \"External\" "
                            + "and none of the tags contains the word \"Internal\"."
                        )
                        #we'll blindly assume that we are dealing with "WALL-OUTER"
                        thisNoodleType = "WALL-OUTER"
                        pass
                else:
                    #the default is to assume that noodleType has not changed.
                    thisNoodleType = noodleType

                #As far as I can tell, there is no good way to detect which moves in the jsontoolpath correspond to Cura's concepts of SKIN, SKIRT, SUPPORT-INTERFACE, and PRIME-TOWER. 

                if thisNoodleType != noodleType:
                    noodleType =  thisNoodleType
                    outputGcodeFile.write(";TYPE:" + str(noodleType) + "\n")

                outputGcodeFile.write(
                    "G1 X{} Y{} Z{} E{} F{}".format(
                        command['parameters']['x'],
                        command['parameters']['y'],
                        command['parameters']['z'],
                        command['parameters']['a'],
                        command['parameters']['feedrate'] * 60
                    ) + "\n"
                )
            elif function == 'comment':
                comment: str = command['parameters']['comment']
                outputGcodeFile.write("; " + comment + "\n")
                upperPositionPrefix = "Upper Position"

                #watch for a comment that looks like "Upper Position  0.05", and, upon change,
                # increment layer number and emit a ";LAYER:" comment.
                if comment.startswith(upperPositionPrefix):
                    thisUpperPosition = float( 
                        re.search( pattern='[0123456789\.\+\-]+',  string=comment[len(upperPositionPrefix):]   ).group(0)
                    )   
                    if thisUpperPosition != lastUpperPosition:
                        layerNumber += 1
                        outputGcodeFile.write(";LAYER:" + str(layerNumber) + "\n")
                        lastUpperPosition = thisUpperPosition
                    else:
                        # if we get here, then we must have encountered an  "Upper Position" comment
                        # with the same value as the last "Upper Position" comment.
                        pass
                
            elif function == 'set_toolhead_temperature':
                pass
            elif function == 'toggle_fan':
                pass
            elif function == 'fan_duty':
                pass
            else:
                pass
        if progressReportingCallback: progressReportingCallback((index + 1)/len(toolpath))
    # print("\n") 
    # print("encountered the following tags:\n" + indentAllLines("\n".join(sorted(allTags))) + "\n")        
    # print("encountered the following functions:\n" + indentAllLines("\n".join(sorted(allFunctions))) + "\n")        

    
    # add a comment like ";LAYER:-6" at the beginning of each layer

    # add comments like:
    #    ";TYPE:FILL"
    #    ";TYPE:SKIN"
    #    ";TYPE:SUPPORT"
    #    ";TYPE:SUPPORT-INTERFACE"
    #    ";TYPE:WALL-INNER"
    #    ";TYPE:WALL-OUTER"
    #


# if args.miraclegrue_config_schema_file and args.output_annotated_miraclegrue_config_file:
if args.output_annotated_miraclegrue_config_file:
    # generate an annotated hjson version of the config file, by
    # adding the descriptions in the schema as comments.
    # schema = json.load(open(pathlib.Path(args.miraclegrue_config_schema_file[0]).resolve() ,'r'))
    process = subprocess.run(
        args=[
            str(miraclegrue_executable_path),
            "--config-schema"   
        ],
        capture_output = True,
        text=True
    )
    schema = json.loads(process.stdout)
    # oldSchema = json.load(open(pathlib.Path(args.old_miraclegrue_config_schema_file[0]).resolve(),'r'))
    # oldMiraclegrueConfig = json.load(open(pathlib.Path(args.old_miraclegrue_config_file[0]).resolve(),'r'))
    # we might consider running the config through miraclegrue and letting mircalegrue remove any invalid values.

    with open(pathlib.Path(args.output_annotated_miraclegrue_config_file[0]).resolve() ,'w') as annotatedConfigFile:
        annotatedConfigFile.write(
            dumpsAnnotatedHjsonValue(
                value=miraclegrueConfig,
                schema=schema,
                path=[]
            )
        )

# generate several temporary files, which we will use during the slicing/makerbot packaging process
tempFilePaths = dict()
for key in ["miraclegrue_config", "metadata", "jsontoolpath", "gcode"]:
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=(".jsontoolpath" if key == "jsontoolpath" else "")) as x:
        tempFilePaths[key] = pathlib.Path(x.name).resolve()
tempThumbnailDirectory = tempfile.TemporaryDirectory()


json.dump(miraclegrueConfig, open(tempFilePaths["miraclegrue_config"],'w'), sort_keys=True, indent=4)

if False and output_makerbot_file_path:
    subprocessArgs = [
        str(makerware_python_executable_path),
        str(makerware_sliceconfig_path),
        "--status-updates",
        "--input=" + str(input_model_file_path) +  "",
        "--output=" + str(output_makerbot_file_path) +  "",
        "--machine_id=" + miraclegrueConfig['_bot'] + "",
        "--extruder_ids=" + ",".join(miraclegrueConfig['_extruders']) + "",
        "--material_ids=" + ",".join(miraclegrueConfig['_materials']) + "",
        "--profile=" + str(temporary_miraclegrue_config_file_path) + "" ,
        "slice"
    ]

    process = subprocess.Popen(
        cwd=makerware_python_working_directory_path,
        args=subprocessArgs,
        # capture_output = True,
        text=True,
        stdout=subprocess.PIPE
    )


    # for line in iter(process.stdout.readline, 'b'):
    #     if line:
    #         # sys.stdout.write(line)
    #         print(line)
    #     else:
    #         break
   
   
    # while True:
    #     output = process.stdout.readline()
    #     if output == '' and process.poll() is not None:
    #         break
    #     if output:
    #         now = datetime.datetime.now()
    #         print(now.strftime("%Y-%m-%d %H:%M:%S") + " " + str(now.microsecond) + " " + ": " + output.strip())
    #         sys.stdout.flush()

    progressBar = MyProgressBar("sliceconfig")
    for line in iter(process.stdout.readline, 'b'):
        if line:
            #attempt to interpret line as a json expression.
            jsonObject = None
            try:
                jsonObject: dict = json.loads(line)
            except json.decoder.JSONDecodeError as error:
                # sys.stdout.write(line); sys.stdout.flush()
                # # curiously, on some shells (for instance, the shell within notepad++ and git bash), 
                # # the output from this script was being accumulated in a  buffer and only dumped to stdout 
                # # once the process had completed.  The fix was to add the sys.stdout.flush() call above.
                pass
            else:
                progressBar.setProgressAndUpdate(float(jsonObject.get("progress"))/100)

        else:
            break
    process.wait()
    progressBar.setProgressAndUpdate(1)
    progressBar.finish()
    # print("process.args: " + "\n" + indentAllLines("\n".join(process.args)))
    # print("process.stdout: " + str(process.stdout))
    # print("process.stderr: " + str(process.stderr))
    print("process.returncode: " + str(process.returncode))
    print("temporary_miraclegrue_config_file_path: " + str(temporary_miraclegrue_config_file_path))

if output_gcode_file_path or output_json_toolpath_file_path or output_metadata_file_path or output_makerbot_file_path: 
    subprocessArgs = [str(miraclegrue_executable_path),
        "--json-progress", # Display progress messages in JSON format
        "--config=" + str(tempFilePaths["miraclegrue_config"])
    ]

    if output_gcode_file_path: subprocessArgs.append("--gcode-toolpath-output=" + str(tempFilePaths["gcode"]))
    if output_json_toolpath_file_path or output_makerbot_file_path or output_previewable_gcode_file_path: subprocessArgs.append("--json-toolpath-output=" + str(tempFilePaths["jsontoolpath"]))
    if output_metadata_file_path or output_makerbot_file_path: subprocessArgs.append("--metadata-output=" + str(tempFilePaths["metadata"]))
    if output_miraclegrue_log_file_path: 
        subprocessArgs.append("--log-file=" + str(output_miraclegrue_log_file_path))
        subprocessArgs.append("--log-level=" + "FFF")
        # --log-level level                     
        # Verbosity of the slicer output log. 
        # Must be one of ERROR, WARNING, INFO, 
        # FINE, FINER, FINEST or E, W, I, F, FF, 
        # FFF respectively
        subprocessArgs.append("--no-log-format")
        

    subprocessArgs.append(str(input_model_file_path))
     

    process = subprocess.Popen(
        cwd=makerware_python_working_directory_path,
        args=subprocessArgs,
        # capture_output = True,
        text=True,
        stdout=subprocess.PIPE
    ) 

    # progressBar = MyProgressBar("miracle_grue", file=sys.stdout)
    progressBar = MyProgressBar("miracle_grue")
    for line in iter(process.stdout.readline, 'b'): 
        if line:
            #attempt to interpret line as a json expression.
            jsonObject = None
            try:
                jsonObject: dict = json.loads(line)
            except json.decoder.JSONDecodeError as error:
                # sys.stdout.write(line); sys.stdout.flush()
                # # curiously, on some shells (for instance, the shell within notepad++ and git bash), 
                # # the output from this script was being accumulated in a  buffer and only dumped to stdout 
                # # once the process had completed.  The fix was to add the sys.stdout.flush() call above.
                pass
            else:
                progressBar.setProgressAndUpdate(float(jsonObject.get("totalPercentComplete"))/100)
                sys.stdout.flush()
        else:
            break
    process.wait()
    progressBar.setProgressAndUpdate(1)
    progressBar.finish()
    # print("process.args: " + "\n" + indentAllLines("\n".join(process.args)))
    # print("process.stdout: " + str(process.stdout))
    # print("process.stderr: " + str(process.stderr))
    print("process.returncode: " + str(process.returncode))

    if output_metadata_file_path: shutil.copyfile(tempFilePaths["metadata"], output_metadata_file_path)
    if output_json_toolpath_file_path: shutil.copyfile(tempFilePaths["jsontoolpath"], output_json_toolpath_file_path)
    if output_gcode_file_path: shutil.copyfile(tempFilePaths["gcode"], output_gcode_file_path)

    if output_previewable_gcode_file_path:
        progressBar = MyProgressBar("gcode")
        generatePreviewableGcode(
            inputJsontoolpathFile=open(tempFilePaths["jsontoolpath"],'r'),  
            outputGcodeFile=open(output_previewable_gcode_file_path,'w'), 
            progressReportingCallback=progressBar.setProgressAndUpdate
        )
        progressBar.finish()
    if output_makerbot_file_path:
        subprocessArgs = [
            str(makerware_python_executable_path),
            str(makerware_sliceconfig_path),
            "--status-updates",
            "--input=" + str(tempFilePaths["jsontoolpath"]),
            "--output=" + str(output_makerbot_file_path),
            "--machine_id=" + miraclegrueConfig['_bot'],
            "--extruder_ids=" + ",".join(miraclegrueConfig['_extruders']),
            "--material_ids=" + ",".join(miraclegrueConfig['_materials']),
            "--profile=" + str(tempFilePaths["miraclegrue_config"]),
            "--metadata=" + str(tempFilePaths["metadata"]),
            # "--thumbnail-dir=" + str(pathlib.Path(tempThumbnailDirectory.name).resolve()),
            # having nothing in the thumbnail dir causes an error.  Therefore, we will only pass the thumbnail-dir option if we have thumbnail images.
            "package_makerbot"
        ]

        process = subprocess.Popen(
            cwd=makerware_python_working_directory_path,
            args=subprocessArgs,
            # capture_output = True,
            text=True,
            stdout=subprocess.PIPE
        )

        progressBar = MyProgressBar("sliceconfig")
        for line in iter(process.stdout.readline, 'b'):
            if line:
                #attempt to interpret line as a json expression.
                jsonObject = None
                try:
                    jsonObject: dict = json.loads(line)
                except json.decoder.JSONDecodeError as error:
                    # sys.stdout.write(line); sys.stdout.flush()
                    # # curiously, on some shells (for instance, the shell within notepad++ and git bash), 
                    # # the output from this script was being accumulated in a  buffer and only dumped to stdout 
                    # # once the process had completed.  The fix was to add the sys.stdout.flush() call above.
                    pass
                else:
                    progressBar.setProgressAndUpdate(float(jsonObject.get("progress"))/100)
            else:
                break
        process.wait()
        progressBar.setProgressAndUpdate(1)
        progressBar.finish()
        # print("process.args: " + "\n" + indentAllLines("\n".join(process.args)))
        print("process.returncode: " + str(process.returncode))






