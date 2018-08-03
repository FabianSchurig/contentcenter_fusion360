import adsk.core, adsk.fusion, adsk.cam, traceback
import sys

sys.path.append("./Modules")

import json
import requests

# global set of event handlers to keep them referenced for the duration of the command
handlers = []
_app = adsk.core.Application.cast(None)
_ui = adsk.core.UserInterface.cast(None)
num = 0
HOST = "https://custom.hk-fs.de"
lastImported = None
componentStack = []
timelineGroupStack = []
parameterStack = []
occurences = []
jointOrigins = []
idStack = []

def initialize():
    global num, lastImported, componentStack, timelineGroupStack, parameterStack, occurences, jointOrigins, idStack
    num = 0
    lastImported = None
    componentStack = []
    timelineGroupStack = []
    parameterStack = []
    occurences = []
    jointOrigins = []
    idStack = []


def setMaterial(componentName, materialLibraryId, materialId):
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    component = design.allComponents.itemByName(componentName)
    material = _app.materialLibraries.item(materialLibraryId).materials.item(materialId)
    component.material = material
    return {"setMaterial": True}

def getMaterials():
    data = []
    for index, materialLibrary in enumerate(_app.materialLibraries):
        materialLibDict = {}
        materialLibDict['label'] = materialLibrary.name
        materialLibDict['value'] = index
        materials = []
        for jndex, material in enumerate(materialLibrary.materials):
            materialDict = {}
            materialDict['value'] = jndex
            materialDict['label'] = material.name
            materials.append(materialDict)
        materialLibDict['materials'] = materials
        data.append(materialLibDict)
    return data

def getAllJointOrigins():
    global jointOrigins
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)
    jointOrigins = []
    for item in design.allComponents:
        joint = {"component": item.name, "names": []}
        for index, jointOrigin in enumerate(item.allJointOrigins):
            joint['names'].append(jointOrigin.name)
        jointOrigins.append(joint)
    return jointOrigins

def getComponentIndex(parameter):
    global parameterStack
    # find component index by parameter name
    for index, parameterArray in enumerate(parameterStack):
        for parameterDict in parameterArray:
            if 'name' in parameterDict and parameter == parameterDict['name']:
                return index
    return -1

def createJoins(jointOriginDict, jointOriginArray):
    global occurences, componentStack
    #_ui.messageBox(str(jointOriginDict))
    jointOriginComponentName = jointOriginDict['component']
    jointOriginName = jointOriginDict['name']
    jointOriginIndex = jointOriginDict['index']

    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    rootComp = design.rootComponent
    joints = rootComp.joints

    sourceComponent = design.allComponents.itemByName(jointOriginComponentName)

    # delete all existing joints = delete all copies of object
    #_ui.messageBox(str(occurences))

    #for occurence in sourceComponent.allOccurrences:
    #    occurence.deleteMe()
    for occurence in list(occurences):
        if occurence.isValid and occurence.component.name == sourceComponent.name:
            #if occurence.isValid:
            occurences.remove(occurence)
            #occurence.isLightBulbOn = False
            occurence.deleteMe()


    # occurences = []

    for jointOriginSecondDict in jointOriginArray:
        jointOriginSecondComponentName = jointOriginSecondDict['component']
        jointOriginSecondName = jointOriginSecondDict['name']
        jointOriginSecondIndex = jointOriginSecondDict['index']

        # if component name in component Stack = also imported component
        if jointOriginSecondComponentName in componentStack:
            # check componentStack for selected component
            #_ui.messageBox(str(componentStack))
            for secondComponentOccurence in occurences:
                if secondComponentOccurence.component.name == jointOriginSecondComponentName:
                    #_ui.messageBox(str(componentStack))
                    # copy first component
                    occurence = rootComp.occurrences.addExistingComponent(sourceComponent, adsk.core.Matrix3D.create())
                    occurences.append(occurence)
                    # get second component
                    secondComponent = design.allComponents.itemByName(jointOriginSecondComponentName)

                    jointInput = joints.createInput(occurence.component.allJointOrigins[jointOriginIndex].createForAssemblyContext(occurence), secondComponent.allJointOrigins[jointOriginSecondIndex].createForAssemblyContext(secondComponentOccurence))

                    # Set the joint input
                    angle = adsk.core.ValueInput.createByString('0 deg')
                    jointInput.angle = angle
                    offset = adsk.core.ValueInput.createByString('0 cm')
                    jointInput.offset = offset
                    jointInput.setAsRigidJointMotion()

                    #Create the joint
                    joint = joints.add(jointInput)
        else:
            # copy first component
            occurence = rootComp.occurrences.addExistingComponent(sourceComponent, adsk.core.Matrix3D.create())
            occurences.append(occurence)
            # get second component
            secondComponent = design.allComponents.itemByName(jointOriginSecondComponentName)

            # if second component other inserted component iterate through other inserted component and add joint to all jointOrigin of copies

            # save jointOrigins already traversed

            # funktioniert nicht wenn die kopien die selben namen haben
            #jointIndexSecond = 0
            #for index, jointOriginCopy in reversed(list(enumerate(secondComponent.allJointOrigins))):
            #    if jointOriginSecondComponentName == jointOriginCopy.parentComponent.name and jointOriginCopy.name == jointOriginSecondName:
            #        jointIndexSecond = index
            #        break

            #jointIndex = 0
            #for index, jointOriginCopy in enumerate(occurence.component.allJointOrigins):
            #    if jointOriginComponentName == jointOriginCopy.parentComponent.name and jointOriginCopy.name == jointOriginName:
            #        jointIndex = index
            #        break

            jointInput = joints.createInput(occurence.component.allJointOrigins[jointOriginIndex].createForAssemblyContext(occurence), secondComponent.allJointOrigins[jointOriginSecondIndex])

            # Set the joint input
            angle = adsk.core.ValueInput.createByString('0 deg')
            jointInput.angle = angle
            offset = adsk.core.ValueInput.createByString('0 cm')
            jointInput.offset = offset
            jointInput.setAsRigidJointMotion()

            #Create the joint
            joint = joints.add(jointInput)


def adaptThread(parameter, threadExpression):
    global componentStack
    # get the design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    threadSize = design.unitsManager.evaluateExpression(threadExpression)

    componentIndex = getComponentIndex(parameter)

    # get the root component of the active design.
    component = design.allComponents.itemByName(componentStack[componentIndex])

    # iterate through all timeline groups and expand them to work on the thread
    for item in design.timeline.timelineGroups:
        item.isCollapsed = False

    threadFeatures = component.features.threadFeatures

    # get thread
    thread = threadFeatures.item(threadFeatures.count - 1)
    #threadLocation = thread.threadLocation

    isInternal = thread.threadInfo.isInternal

    # query the thread table to get the thread information
    threadDataQuery = threadFeatures.threadDataQuery
    defaultThreadType = threadDataQuery.defaultMetricThreadType
    recommendData = threadDataQuery.recommendThreadData(threadSize, isInternal, defaultThreadType)

    # create the threadInfo according to the query result
    if recommendData[0] :
        threadInfo = threadFeatures.createThreadInfo(isInternal, defaultThreadType, recommendData[1], recommendData[2])
        thread.timelineObject.rollTo(True)
        thread.threadInfo = threadInfo
        design.timeline.moveToEnd()

def adaptThreadLength(parameter, threadExpression):
    global componentStack
    # get the design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    #threadLength = design.unitsManager.evaluateExpression(threadExpression)

    componentIndex = getComponentIndex(parameter)

    # get the root component of the active design.
    component = design.allComponents.itemByName(componentStack[componentIndex])

    # iterate through all timeline groups and expand them to work on the thread
    for item in design.timeline.timelineGroups:
        item.isCollapsed = False

    threadFeatures = component.features.threadFeatures

    # get thread
    thread = threadFeatures.item(threadFeatures.count - 1)
    #threadLocation = thread.threadLocation

    thread.timelineObject.rollTo(True)
    thread.setThreadOffsetLength(adsk.core.ValueInput.createByString(thread.threadOffset.expression), adsk.core.ValueInput.createByString(threadExpression + " -0.0000000001"), adsk.fusion.ThreadLocations.HighEndThreadLocation)
    design.timeline.moveToEnd()

def insertContent(url):
    global lastImported, componentStack, timelineGroupStack, parameterStack
    des = adsk.fusion.Design.cast(_app.activeProduct)

    previousParams = des.userParameters
    previousParamsStr = []
    for u in des.userParameters:
        previousParamsStr.append(u.name)

    importManager = _app.importManager

    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component
    rootComp = design.rootComponent

    # save previous names of components
    previousComponentNames = []
    for item in design.allComponents:
        previousComponentNames.append(item.name)
    previousGroupNames = []
    for item in design.timeline.timelineGroups:
        previousGroupNames.append(item.name)

    r = requests.get(url, allow_redirects=True)
    archiveFileName = url[url.rfind("/")+1:]
    open(archiveFileName, 'wb').write(r.content)


    archiveOptions = importManager.createFusionArchiveImportOptions(archiveFileName)
    # Import archive file to root component
    imported = importManager.importToTarget2(archiveOptions, rootComp)
    lastImported = imported

    # save current names of components
    componentNames = []
    for item in design.allComponents:
        componentNames.append(item.name)
    groupNames = []
    for item in design.timeline.timelineGroups:
        groupNames.append(item.name)

    # compare previous and current to get the inserted component
    addedComponentNames = list(set(componentNames) - set(previousComponentNames))
    addedGroupNames = list(set(groupNames) - set(previousGroupNames))

    for component in addedComponentNames:
        componentStack.append(component)
    for group in addedGroupNames:
        timelineGroupStack.append(group)

    params = des.userParameters
    paramsStr = []
    for u in des.userParameters:
        paramsStr.append(u.name)

    newParameters = list(set(paramsStr) - set(previousParamsStr))
    parameters = []
    for parameter in newParameters:
        param = des.userParameters.itemByName(parameter)
        dict = {'name': parameter, 'expression': param.expression}
        parameters.append(dict)
    parameterStack.append(parameters)

    component = design.allComponents.itemByName(componentStack[-1])
    jointOriginNames = []
    for index, jointOrigin in enumerate(component.allJointOrigins):
        jointOriginNames.append(jointOrigin.name)
    jointOrigins = []
    jointOrigins.append({"component": component.name, "names": jointOriginNames, "selectedPresets": []})

    return {"name": componentStack[-1], "parameters": parameters, "jointOrigins": jointOrigins}

# Event handler for the commandExecuted event.
class ShowPaletteCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # Create and display the palette.
            palette = _ui.palettes.itemById('myPalette')
            if not palette:
                palette = _ui.palettes.add('myPalette', 'Content Center', HOST, True, True, True, 1000, 1000) # ./palette/build/index.html

                # Dock the palette to the right side of Fusion window.
                palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight

                # Add handler to HTMLEvent of the palette.
                onHTMLEvent = MyHTMLEventHandler()
                palette.incomingFromHTML.add(onHTMLEvent)
                handlers.append(onHTMLEvent)

                # Add handler to CloseEvent of the palette.
                onClosed = MyCloseEventHandler()
                palette.closed.add(onClosed)
                handlers.append(onClosed)
            else:
                palette.isVisible = True
        except:
            _ui.messageBox('Command executed failed: {}'.format(traceback.format_exc()))


# Event handler for the commandCreated event.
class ShowPaletteCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            command = args.command
            onExecute = ShowPaletteCommandExecuteHandler()
            command.execute.add(onExecute)
            handlers.append(onExecute)
            initialize()
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler for the commandExecuted event.
class SendInfoCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # Send information to the palette. This will trigger an event in the javascript
            # within the html so that it can be handled.
            palette = _ui.palettes.itemById('myPalette')
            if palette:
                global num
                num += 1
                dict = str({"id": 1, "parameters": num})
                palette.sendInfoToHTML('send', dict)
        except:
            _ui.messageBox('Command executed failed: {}'.format(traceback.format_exc()))


# Event handler for the commandCreated event.
class SendInfoCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            command = args.command
            onExecute = SendInfoCommandExecuteHandler()
            command.execute.add(onExecute)
            handlers.append(onExecute)
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler for the palette close event.
class MyCloseEventHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            return
            #_ui.messageBox('Close button is clicked.')
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler for the palette HTML event.
class MyHTMLEventHandler(adsk.core.HTMLEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            htmlArgs = adsk.core.HTMLEventArgs.cast(args)
            data = json.loads(htmlArgs.data)
            if "id" in data.keys() and "name" in data.keys():
                path = HOST + data['name']
                #_ui.messageBox(path)
                resInput = insertContent(path)
                idStack.append(data["id"])
                args.returnData = str({"id": data['id'],"name": resInput['name'], 'parameters': resInput['parameters'], 'jointOrigins': resInput['jointOrigins'] })

            if 'getJointOrigins' in data.keys():
                initialize()
                jointOrigins = getAllJointOrigins()
                args.returnData = str({'jointOrigins': jointOrigins })

            if 'parameter' in data.keys() and 'expression' in data.keys():
                design = _app.activeProduct
                param = design.userParameters.itemByName(data['parameter'])
                param.expression = data['expression']

                if 'isThreadSize' in data.keys():
                    adaptThread(data['parameter'], data['expression'])
                if 'isThreadLength' in data.keys():
                    adaptThreadLength(data['parameter'], data['expression'])

                args.returnData = str({'expression': param.expression})
            if 'jointOriginSelection' in data.keys() and 'jointOrigin' in data.keys():
                createJoins(data['jointOrigin'], data['jointOriginSelection'])
                args.returnData = str(data)
            if 'getMaterials' in data.keys():
                result = getMaterials()
                args.returnData = str(result)
            if 'setMaterial' in data.keys() and 'name' in data.keys() and 'materialId' in data.keys() and 'materialLibraryId' in data.keys():
                result = setMaterial(data['name'], data['materialLibraryId'], data['materialId'])
                args.returnData = str({"setMaterial": "jio"})
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:
        global _ui, _app
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        # Add a command that displays the panel.
        showPaletteCmdDef = _ui.commandDefinitions.itemById('showPalette')
        if not showPaletteCmdDef:
            showPaletteCmdDef = _ui.commandDefinitions.addButtonDefinition('showPalette', 'Customizable Content Center', 'Show the customizable content center', './resources')

            # Connect to Command Created event.
            onCommandCreated = ShowPaletteCommandCreatedHandler()
            showPaletteCmdDef.commandCreated.add(onCommandCreated)
            handlers.append(onCommandCreated)


        # Add a command under ADD-INS panel which sends information from Fusion to the palette's HTML.
        #sendInfoCmdDef = _ui.commandDefinitions.itemById('sendInfoToHTML')
        #if not sendInfoCmdDef:
        #    sendInfoCmdDef = _ui.commandDefinitions.addButtonDefinition('sendInfoToHTML', 'Send info to Palette', 'Send Info to Palette HTML', '')

            # Connect to Command Created event.
        #    onCommandCreated = SendInfoCommandCreatedHandler()
        #    sendInfoCmdDef.commandCreated.add(onCommandCreated)
        #    handlers.append(onCommandCreated)

        # Add the command to the toolbar.
        panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        cntrl = panel.controls.itemById('showPalette')
        if not cntrl:
            panel.controls.addCommand(showPaletteCmdDef)

        #cntrl = panel.controls.itemById('sendInfoToHTML')
        #if not cntrl:
        #    panel.controls.addCommand(sendInfoCmdDef)
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def stop(context):
    try:
        # Delete the palette created by this add-in.
        palette = _ui.palettes.itemById('myPalette')
        if palette:
            palette.deleteMe()

        # Delete controls and associated command definitions created by this add-ins
        panel = _ui.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        cmd = panel.controls.itemById('showPalette')
        if cmd:
            cmd.deleteMe()
        cmdDef = _ui.commandDefinitions.itemById('showPalette')
        if cmdDef:
            cmdDef.deleteMe()

        cmd = panel.controls.itemById('sendInfoToHTML')
        if cmd:
            cmd.deleteMe()
        cmdDef = _ui.commandDefinitions.itemById('sendInfoToHTML')
        if cmdDef:
            cmdDef.deleteMe()

        _ui.messageBox('Stop addin')
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
