import adsk.core, adsk.fusion, adsk.cam, traceback
import sys
import json
import math
import os
import inspect
import platform
import subprocess

script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
script_dir = os.path.dirname(script_path)
module_dir = os.path.abspath(os.path.join(script_dir, "modules"))
sys.path.append(module_dir)

try:
    import requests
except:
    pass

# global set of event handlers to keep them referenced for the duration of the command
handlers = []
_handlers = []
_app = adsk.core.Application.cast(None)
_ui = adsk.core.UserInterface.cast(None)
num = 0
HOST = "https://custom.hk-fs.de"#"http://localhost:3000"#
lastImported = None
componentStack = []
timelineGroupStack = []
parameterStack = []
occurences = []
jointOrigins = []
idStack = []

isMac = False

# checks if OS is MacOS
if platform.system() == 'Darwin':
    isMac = True

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
        for index, jointOrigin in enumerate(item.jointOrigins):
            joint['names'].append(jointOrigin.name)
        jointOrigins.append(joint)
    return jointOrigins

def getAllJoints():
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)
    joints = []
    for item in design.allComponents:
        componentsJoints = {"component": item.name, "joints": []}
        for index, joint in enumerate(item.joints):
            newJoint = {}
            newJoint['name'] = joint.name

            newJoint['isFlipped'] = joint.isFlipped
            if joint.jointMotion:
                newJoint['jointMotion'] = joint.jointMotion.jointType
            if joint.occurrenceOne:
                newJoint['occurrenceOne'] = joint.occurrenceOne.name
            if joint.occurrenceTwo:
                newJoint['occurrenceTwo'] = joint.occurrenceTwo.name
            componentsJoints['joints'].append(newJoint)
        joints.append(componentsJoints)
    return json.dumps({"joints": joints})

def getComponentIndex(parameter):
    global parameterStack
    # find component index by parameter name
    for index, parameterArray in enumerate(parameterStack):
        for parameterDict in parameterArray:
            if 'name' in parameterDict and parameter == parameterDict['name']:
                return index
    return -1

def getRootName():
    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    rootComp = design.rootComponent
    return rootComp.name

def compareOrigins(firstOrigin,secondOrigin):
    #ui.messageBox(str(firstVertex.geometry.x) + " " + str(firstVertex.geometry.y) + " " + str(firstVertex.geometry.z) + "\n" + str(secondVertex.geometry.x) + " " + str(secondVertex.geometry.y) + " " + str(secondVertex.geometry.z))
    if math.isclose(firstOrigin.x,secondOrigin.x) \
    and math.isclose(firstOrigin.y,secondOrigin.y) \
    and math.isclose(firstOrigin.z,secondOrigin.z):
        return True
    return False

def jointExists(progressDialog, joints, occurrenceOne, occurrencesTwo, jointOriginNameOne, jointOriginNameTwo):
    # Get active design
    _app = adsk.core.Application.get()
    _ui = _app.userInterface
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    rootComp = design.rootComponent
    isRoot = False
    if occurrenceOne.name == rootComp.name:
        isRoot = True

    rstr = "bla\n"
    progressDialog.title = str(' ' + occurrenceOne.name + '.' + jointOriginNameOne + ' - ' + jointOriginNameTwo)
    progressDialog.maximumValue = len(joints)
    progressDialog.reset()
    index = 0

    for joint in joints:
        #_ui.messageBox(str(joint.geometryOrOriginOne.objectType) + "==" + str(joint.geometryOrOriginOne.objectType) + "\n==" + str(adsk.fusion.JointOrigin.classType()))
        for occurrenceTwo in occurrencesTwo:
            #_ui.messageBox(str(joint.geometryOrOriginOne.entityOne.objectType) + "==" + str(adsk.fusion.JointOrigin.classType()))
            if joint.geometryOrOriginOne.objectType == adsk.fusion.JointGeometry.classType() \
                and joint.geometryOrOriginTwo.objectType == adsk.fusion.JointGeometry.classType() \
                and occurrenceTwo.name == joint.occurrenceOne.name or isRoot:
                    if isRoot:
                        one = occurrenceOne.jointOrigins.itemByName(jointOriginNameOne).geometry.origin
                    else:
                        one = occurrenceOne.component.jointOrigins.itemByName(jointOriginNameOne).createForAssemblyContext(occurrenceOne).geometry.origin
                    two = joint.geometryOrOriginTwo.origin
                    three = joint.geometryOrOriginOne.origin
                    four = occurrenceTwo.component.jointOrigins.itemByName(jointOriginNameTwo).createForAssemblyContext(occurrenceTwo).geometry.origin

                    if compareOrigins(one,three) and compareOrigins(two,four) or compareOrigins(one,two) and compareOrigins(three,four):
                        #_ui.messageBox("yes")
                        return True
        index += 1
        progressDialog.progressValue = index

    '''
        rstr += occurrenceOne.name + "\n"
        if joint.occurrenceTwo:
            rstr += joint.occurrenceTwo.name + "\n"
        rstr += occurrenceTwo.name + "\n"
        rstr += joint.occurrenceOne.name + "\n"
        rstr += joint.name + "\n"

        rstr += str(one.x) + " " + str(one.y) + " "+ str(one.z) + "\n"
        rstr += str(two.x) + " " + str(two.y) + " "+ str(two.z) + "\n"
        rstr += str(three.x) + " " + str(three.y) + " "+ str(three.z) + "\n"
        rstr += str(four.x) + " " + str(four.y) + " "+ str(four.z) + "\n"
        rstr += str(compareOrigins(one,three)) + " " + str(compareOrigins(four,two)) + "\n"
        _ui.messageBox(str(rstr))
        #return True

    _ui.messageBox(str((joint.geometryOrOriginOne.name == occurrenceOne.name and joint.geometryOrOriginTwo.name == occurrenceTwo.name \
    or joint.geometryOrOriginTwo.name == occurrenceOne.name and joint.geometryOrOriginOne.name == occurrenceTwo.name)))

    if (joint.geometryOrOriginOne.name == occurrenceOne.name and joint.geometryOrOriginTwo == occurrenceTwo.geometry \
    or joint.geometryOrOriginTwo.name == occurrenceOne.name and joint.geometryOrOriginOne == occurrenceTwo.name):
        return True'''
    #_ui.messageBox(str(rstr))
    return False

def newJoints(newJoints):
    jointOriginDictOne = newJoints['jointOrigin']
    jointOriginList = newJoints['jointOriginList']

    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    rootComp = design.rootComponent
    joints = rootComp.joints

    # get both components
    componentOne = design.allComponents.itemByName(jointOriginDictOne['component'])

    # get occurrences of each component
    occurrencesOne = rootComp.occurrencesByComponent(componentOne)

    progressDialog = _ui.createProgressDialog()
    progressDialog.isBackgroundTranslucent = False
    progressLen = len(jointOriginList)
    progressDialog.show(str('Dupe ' + componentOne.name), 'Percentage: %p, Current Value: %v, Total steps: %m', 0, progressLen)

    i = 0

    for jointOriginDictTwo in jointOriginList:


        componentTwo = design.allComponents.itemByName(jointOriginDictTwo['component'])
        occurrencesTwo = rootComp.occurrencesByComponent(componentTwo)

        if componentTwo.name == rootComp.name:
            hasJoint = jointExists(progressDialog, joints, componentTwo, occurrencesOne, jointOriginDictTwo['name'], jointOriginDictOne['name'])
            progressDialog.reset()
            progressDialog.maximumValue = progressLen
            progressDialog.progressValue = i
            if not hasJoint:
                # make a new copy
                newOccurrence = rootComp.occurrences.addExistingComponent(componentOne, adsk.core.Matrix3D.create())

                jointInput = joints.createInput(newOccurrence.component.jointOrigins.itemByName(jointOriginDictOne['name']).createForAssemblyContext(newOccurrence), componentTwo.jointOrigins.itemByName(jointOriginDictTwo['name']))

                # Set the joint input
                angle = adsk.core.ValueInput.createByString('0 deg')
                jointInput.angle = angle
                offset = adsk.core.ValueInput.createByString('0 cm')
                jointInput.offset = offset
                jointInput.setAsRigidJointMotion()

                #Create the joint
                joint = joints.add(jointInput)
        else:
            for occurrenceOne in occurrencesOne:

                # check occurrences for each component if joint already exists
                # if occurenceOne already have an existing joint between both components skip it
                hasJoint = jointExists(progressDialog, joints, occurrenceOne, occurrencesTwo, jointOriginDictOne['name'], jointOriginDictTwo['name'])
                progressDialog.reset()
                progressDialog.maximumValue = progressLen
                progressDialog.progressValue = i
                if not hasJoint:
                    # make a new copy
                    newOccurrence = rootComp.occurrences.addExistingComponent(componentTwo, adsk.core.Matrix3D.create())

                    jointInput = joints.createInput(newOccurrence.component.jointOrigins.itemByName(jointOriginDictTwo['name']).createForAssemblyContext(newOccurrence), componentOne.jointOrigins.itemByName(jointOriginDictOne['name']).createForAssemblyContext(occurrenceOne))

                    # Set the joint input
                    angle = adsk.core.ValueInput.createByString('0 deg')
                    jointInput.angle = angle
                    offset = adsk.core.ValueInput.createByString('0 cm')
                    jointInput.offset = offset
                    jointInput.setAsRigidJointMotion()

                    #Create the joint
                    joint = joints.add(jointInput)
        i += 1
        progressDialog.progressValue = i
    progressDialog.hide()
    '''
    for occurrenceTwo in occurrencesTwo:
        hasJoint = jointExists(joints, occurrenceTwo, occurrencesOne, jointOriginDictTwo['name'], jointOriginDictOne['name'])

        if not hasJoint:
            # make a new copy
            newOccurrence = rootComp.occurrences.addExistingComponent(componentOne, adsk.core.Matrix3D.create())

            jointInput = joints.createInput(newOccurrence.component.jointOrigins.itemByName(jointOriginDictOne['name']).createForAssemblyContext(newOccurrence), componentTwo.jointOrigins.itemByName(jointOriginDictTwo['name']).createForAssemblyContext(occurrenceTwo))

            # Set the joint input
            angle = adsk.core.ValueInput.createByString('0 deg')
            jointInput.angle = angle
            offset = adsk.core.ValueInput.createByString('0 cm')
            jointInput.offset = offset
            jointInput.setAsRigidJointMotion()

            #Create the joint
            joint = joints.add(jointInput)'''

def newJointsByOccurrences(newJoints):
    jointOriginDictOne = newJoints['jointOrigin']
    jointOriginList = newJoints['jointOriginList']

    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    rootComp = design.rootComponent
    joints = rootComp.joints

    # get both components
    componentOne = design.allComponents.itemByName(jointOriginDictOne['component'])

    progressDialog = _ui.createProgressDialog()
    progressDialog.isBackgroundTranslucent = False
    progressLen = len(jointOriginList)
    progressDialog.show(str('Dupe ' + componentOne.name), 'Percentage: %p, Current Value: %v, Total steps: %m', 0, progressLen)

    i = 0

    for jointOriginDictTwo in jointOriginList:
        if jointOriginDictTwo['component'] == rootComp.name:
            jointOriginDictTwo['occurrence'] = rootComp.name
            componentTwo = rootComp
        else:
            occurrenceTwo = rootComp.allOccurrences.itemByName(jointOriginDictTwo['occurrence'])
            componentTwo = occurrenceTwo.component
        if jointOriginDictTwo['occurrence']:
            #occurrencesTwo = rootComp.occurrencesByComponent(componentTwo)

            if jointOriginDictTwo['component'] == rootComp.name:
                # make a new copy
                newOccurrence = rootComp.occurrences.addExistingComponent(componentOne, adsk.core.Matrix3D.create())

                jointInput = joints.createInput(newOccurrence.component.jointOrigins.itemByName(jointOriginDictOne['name']).createForAssemblyContext(newOccurrence), componentTwo.jointOrigins.itemByName(jointOriginDictTwo['name']))

                # Set the joint input
                angle = adsk.core.ValueInput.createByString('0 deg')
                jointInput.angle = angle
                offset = adsk.core.ValueInput.createByString('0 cm')
                jointInput.offset = offset
                jointInput.setAsRigidJointMotion()

                #Create the joint
                joint = joints.add(jointInput)
            else:
                # make a new copy
                newOccurrence = rootComp.occurrences.addExistingComponent(componentOne, adsk.core.Matrix3D.create())

                jointInput = joints.createInput(newOccurrence.component.jointOrigins.itemByName(jointOriginDictOne['name']).createForAssemblyContext(newOccurrence), componentTwo.jointOrigins.itemByName(jointOriginDictTwo['name']).createForAssemblyContext(occurrenceTwo))

                # Set the joint input
                angle = adsk.core.ValueInput.createByString('0 deg')
                jointInput.angle = angle
                offset = adsk.core.ValueInput.createByString('0 cm')
                jointInput.offset = offset
                jointInput.setAsRigidJointMotion()

                #Create the joint
                joint = joints.add(jointInput)
        i += 1
        progressDialog.progressValue = i
    progressDialog.hide()

def deleteJoints(deleteJoint, deleteComponents):
    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    rootComp = design.rootComponent
    joints = rootComp.joints

    component = joints.itemByName(deleteJoint).occurrenceOne.component
    # componentTwo = joints.itemByName(deleteJoint).occurrenceOne.component
    l = list(rootComp.allOccurrencesByComponent(component))
    # lTwo = list(rootComp.allOccurrencesByComponent(componentTwo))
    if deleteComponents:
        progressDialog = _ui.createProgressDialog()
        progressDialog.isBackgroundTranslucent = False
        progressLen = len(l)
        progressDialog.show(str('Delete ' + component.name), 'Percentage: %p, Current Value: %v, Total steps: %m', 0, progressLen)

        for index, occurrence in enumerate(l):
            if not index < 1:
                try:
                    occurrence.timelineObject.rollTo(False)
                except:
                    pass
                occurrence.deleteMe()
                progressDialog.progressValue = index
        design.timeline.moveToEnd()
        # for index, occurrence in enumerate(lTwo):
        #     if not index < 1:
        #         occurrence.deleteMe()
        progressDialog.hide()

    else:
        occurrence = joints.itemByName(deleteJoint).occurrenceOne
        occurrenceTwo = joints.itemByName(deleteJoint).occurrenceTwo
        try:
            occurrence.timelineObject.rollTo(False)
        except:
            pass
        occurrence.deleteMe()
        design.timeline.moveToEnd()
        # if occurrenceTwo and len(occurrenceTwo.joints) < 1:
        #     occurrenceTwo.timelineObject.rollTo(False)
        #     occurrenceTwo.deleteMe()
        #     design.timeline.moveToEnd()


def highlightOccurrence(occurrenceOne, color=(50,180,10,255)):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent

    # Create the color effect.
    r,g,b,a = color
    redColor = adsk.core.Color.create(r,g,b,a)
    solidColor = adsk.fusion.CustomGraphicsSolidColorEffect.create(redColor)

    mx = (occurrenceOne.boundingBox.minPoint.x+occurrenceOne.boundingBox.maxPoint.x)/2
    my = (occurrenceOne.boundingBox.minPoint.y+occurrenceOne.boundingBox.maxPoint.y)/2

    vx = occurrenceOne.boundingBox.maxPoint.x
    vy = occurrenceOne.boundingBox.maxPoint.y

    wx = occurrenceOne.boundingBox.minPoint.x
    wy = occurrenceOne.boundingBox.minPoint.y

    angle = math.radians(90)

    tx = mx + math.cos(angle) * (wx - mx) - math.sin(angle) * (wy - my)
    ty = my + math.sin(angle) * (wx - mx) + math.cos(angle) * (wy - my)

    sx = mx + math.cos(angle) * (vx - mx) - math.sin(angle) * (vy - my)
    sy = my + math.sin(angle) * (vx - mx) + math.cos(angle) * (vy - my)


    coordArray = [occurrenceOne.boundingBox.minPoint.x, occurrenceOne.boundingBox.minPoint.y, occurrenceOne.boundingBox.minPoint.z,
              occurrenceOne.boundingBox.minPoint.x, occurrenceOne.boundingBox.minPoint.y, occurrenceOne.boundingBox.maxPoint.z,
              sx,sy,occurrenceOne.boundingBox.maxPoint.z,
              sx,sy,occurrenceOne.boundingBox.minPoint.z,
              tx,ty,occurrenceOne.boundingBox.maxPoint.z,
              tx,ty,occurrenceOne.boundingBox.minPoint.z,
              occurrenceOne.boundingBox.maxPoint.x, occurrenceOne.boundingBox.maxPoint.y, occurrenceOne.boundingBox.minPoint.z,
              occurrenceOne.boundingBox.maxPoint.x, occurrenceOne.boundingBox.maxPoint.y, occurrenceOne.boundingBox.maxPoint.z]
    coords = adsk.fusion.CustomGraphicsCoordinates.create(coordArray)

    # Create a graphics group on the root component.
    graphics = root.customGraphicsGroups.add()

    # Create the graphics body.
    lineIndices = [ 0,1, 0,3, 0,5, 1,2, 2,7, 3,6, 6,7, 6,5, 4,5, 4,7, 4,1, 3,2] #
    lines = graphics.addLines(coords, lineIndices, False)
    lines.weight = 2
    lines.color = solidColor

    # Refresh the graphics.
    _app.activeViewport.refresh()

def highlightJointByName(jointName):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent

    joints = root.joints

    occurrence = joints.itemByName(jointName).occurrenceOne
    occurrenceTwo = joints.itemByName(jointName).occurrenceTwo

    for item in list(root.customGraphicsGroups):
        item.deleteMe()

    _app.activeViewport.refresh()

    if occurrenceTwo:
        highlightOccurrence(occurrenceTwo, color=(200,50,10,255))
    else:
        highlightOccurrence(joints.itemByName(jointName).parentComponent, color=(200,50,10,255))

    highlightOccurrence(occurrence)

def highlightOccurrencesByComponentName(componentName):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent

    for item in list(root.customGraphicsGroups):
        item.deleteMe()

    _app.activeViewport.refresh()

    if componentName == root.name:
        highlightOccurrence(root, color=(200,50,10,255))
    else:
        # get both components
        componentOne = design.allComponents.itemByName(componentName)

        # get occurrences of each component
        occurrencesOne = root.occurrencesByComponent(componentOne)

        for occurrenceOne in occurrencesOne:
            highlightOccurrence(occurrenceOne)

def adaptThread(componentName, parameter, threadExpression):
    # get the design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    threadSize = design.unitsManager.evaluateExpression(threadExpression)

    # get the root component of the active design.
    component = design.allComponents.itemByName(componentName)

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

def adaptThreadLength(componentName, parameter, threadExpression):
    # get the design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    #threadLength = design.unitsManager.evaluateExpression(threadExpression)

    # get the root component of the active design.
    component = design.allComponents.itemByName(componentName)

    # iterate through all timeline groups and expand them to work on the thread
    for item in design.timeline.timelineGroups:
        item.isCollapsed = False

    threadFeatures = component.features.threadFeatures

    # get thread
    thread = threadFeatures.item(threadFeatures.count - 1)
    #threadLocation = thread.threadLocation

    thread.timelineObject.rollTo(True)
    thread.setThreadOffsetLength(adsk.core.ValueInput.createByString(thread.threadOffset.expression), adsk.core.ValueInput.createByString(threadExpression + " -0.0000000001"), thread.threadLocation)
    design.timeline.moveToEnd()

def insertContent(id, name, url):
    global lastImported, componentStack, timelineGroupStack, parameterStack, isMac, script_dir
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

    downloadDir = os.path.join(script_dir, 'downloads')
    os.makedirs(downloadDir, exist_ok=True)

    keepcharacters = (' ','.','_')
    archiveFileNameUn = name + '.f3d' #url[url.rfind("/")+1:]
    archiveFileName = os.path.join(downloadDir, "".join(c for c in archiveFileNameUn if c.isalnum() or c in keepcharacters).rstrip())
    if isMac:
        subprocess.call(['curl', '-o', archiveFileName, '-L', url])
    else:
        r = requests.get(url, allow_redirects=True)
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

    #des.userParameters.add("contentCenterID", adsk.core.ValueInput.createByString("0"), "", str(id))

    params = des.userParameters
    paramsStr = []
    for u in des.userParameters:
        paramsStr.append(u.name)

    newParameters = list(set(paramsStr) - set(previousParamsStr))
    parameters = []
    for parameter in newParameters:
        des.userParameters.itemByName(parameter).comment = str(id)
        param = des.userParameters.itemByName(parameter)
        dict = {'name': parameter, 'expression': param.expression, 'comment': param.comment}
        parameters.append(dict)

    parameterStack.append(parameters)

    component = design.allComponents.itemByName(componentStack[-1])
    jointOriginNames = []
    for index, jointOrigin in enumerate(component.allJointOrigins):
        jointOriginNames.append(jointOrigin.name)
    jointOrigins = []
    jointOrigins.append({"component": component.name, "names": jointOriginNames, "selectedPresets": []})

    return {"name": componentStack[-1], "parameters": parameters, "jointOrigins": jointOrigins}

def find(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1

def getParameters():
    design = _app.activeProduct
    list = []

    for param in design.userParameters:
        dict = {}
        dict['name'] = param.name
        dict['expression'] = param.expression
        dict['comment'] = param.comment
        list.append(dict)
    return json.dumps({'parameters': list})

def getUserParameters():
    global _app
    design = _app.activeProduct

    componentNames = []
    modelParamNames = []
    userParamNames = []

    documentName = design.parentDocument.name

    for component in design.allComponents:
        if component.parentDesign.parentDocument.name == documentName:
            componentNames.append(component.name)

            # getting all parameter names for every component
            modelNames = []
            try:
                for model in component.modelParameters:
                    modelNames.append(model.name)
                modelParamNames.append(modelNames)
            except:
                modelParamNames.append([])
                pass

    for userParam in design.userParameters:
        for param in userParam.dependentParameters:
            name = param.name
            for i, modelNames in enumerate(modelParamNames):
                if name in modelNames:
                    index = find(userParamNames, 'component', componentNames[i])
                    if index > -1:
                        k = find(userParamNames[index]['parameters'], 'name', userParam.name)
                        if not k > -1:
                            userParamNames[index]['parameters'].append({"name": userParam.name, "expression": userParam.expression, "comment": userParam.comment})
                    else:
                        d = {}
                        d['component'] = componentNames[i]
                        d['parameters'] = [{"name": userParam.name, "expression": userParam.expression, "comment": userParam.comment}]
                        userParamNames.append(d)

    return json.dumps({'userParameters': userParamNames})

# Event handler that reacts to any changes the user makes to any of the command inputs.
class SelectionInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        global strInput
        try:
            eventArgs = adsk.core.InputChangedEventArgs.cast(args)
            inputs = eventArgs.inputs
            cmdInput = eventArgs.input

            if cmdInput.id == 'selection':
                selectionInput = inputs.itemById('selection')

        except:
            _ui().messageBox('Failed:\n{}'.format(traceback.format_exc()))

# Event handler that reacts to any changes the user makes to any of the command inputs.
class SelectionExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        global strInput
        try:
            eventArgs = adsk.core.CommandEventArgs.cast(args)

            # Code to react to the event.
            app = adsk.core.Application.get()
            ui  = app.userInterface

            command = args.firingEvent.sender
            inputs = command.commandInputs

            for input in inputs:
                if input.id == 'selection':
                    selectionInput = inputs.itemById('selection')

            list = []
            for i in range(selectionInput.selectionCount):
                dict = {}
                if selectionInput.selection(i).entity:
                    dict['objectType'] = selectionInput.selection(i).entity.objectType
                    dict['name'] = selectionInput.selection(i).entity.name
                    if selectionInput.selection(i).entity.parentComponent:
                        dict['component'] = selectionInput.selection(i).entity.parentComponent.name
                    if selectionInput.selection(i).entity.assemblyContext:
                        dict['occurrence'] = selectionInput.selection(i).entity.assemblyContext.name
                list.append(dict)
            #ui.messageBox(str(list))

            palette = _ui.palettes.itemById('myPalette')
            if palette:
                dict = str({"inputSelections": list})
                palette.sendInfoToHTML('send', dict)

        except:
            _ui().messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler that reacts to when the command is destroyed. This terminates the script.
class SelectionDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        global _ui
        try:
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            #adsk.terminate()
            # Get the existing command definition or create it if it doesn't already exist.
            cmdDef = _ui.commandDefinitions.itemById('cmdInputSelections')
            cmdDef.deleteMe()
        except:
            _ui().messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler that reacts when the command definitio is executed which
# results in the command being created and this event being fired.
class SelectionCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)

            # Connect to the command destroyed event.
            onDestroy = SelectionDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            # Connect to the input changed event.
            onInputChanged = SelectionInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)

            # Connect to the execute event.
            onExecute = SelectionExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs

            # Create a selection input.
            selectionInput = inputs.addSelectionInput('selection', 'Select', 'Basic select command input')
            selectionInput.addSelectionFilter("JointOrigins")
            # selectionInput.addSelectionFilter("Vertices")
            # selectionInput.addSelectionFilter("SketchCurves")
            # selectionInput.addSelectionFilter("SketchPoints")
            selectionInput.setSelectionLimits(0)

        except:
            _ui().messageBox('Failed:\n{}'.format(traceback.format_exc()))


def createInputSelections():
    try:
        global _app, _ui, strInput, _handlers
        _app = adsk.core.Application.get()
        _ui = _app.userInterface


        cmdDef = _ui.commandDefinitions.itemById('cmdInputSelections')
        if not cmdDef:
            cmdDef = _ui.commandDefinitions.addButtonDefinition('cmdInputSelections', 'Select Inputs for Joints', 'Sample to demonstrate various command inputs.')

            # Connect to the command created event.
            onCommandCreated = SelectionCreatedHandler()
            cmdDef.commandCreated.add(onCommandCreated)
            _handlers.append(onCommandCreated)

            # Execute the command definition.
            cmdDef.execute()
        else:
            try:
                cmdDef.deleteMe()
            except:
                pass

        # Prevent this module from being terminated when the script returns, because we are waiting for event handlers to fire.
        #adsk.autoTerminate(False)
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

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
            if 'id' in data.keys() and 'name' in data.keys():
                path = HOST + data['url']
                try:
                    resInput = insertContent(data['id'], data['name'], path)
                    idStack.append(data["id"])
                except:
                    pass
                args.returnData = str({"id": data['id'],"name": resInput['name'], 'parameters': resInput['parameters'], 'jointOrigins': resInput['jointOrigins'] })

            if 'getJointOrigins' in data.keys():
                initialize()
                jointOrigins = getAllJointOrigins()
                args.returnData = str({'jointOrigins': jointOrigins })

            if 'getJoints' in data.keys():
                initialize()
                joints = getAllJoints()
                args.returnData = str(joints)

            if 'getParameters' in data.keys():
                try:
                    parameters = getUserParameters() # old getParameters()
                except:
                    pass
                args.returnData = str(parameters)

            if 'parameter' in data.keys() and 'expression' in data.keys():
                design = _app.activeProduct
                try:
                    param = design.userParameters.itemByName(data['parameter'])
                    param.expression = data['expression']
                    design.timeline.moveToEnd()
                except:
                    pass

                if 'isThreadSize' in data.keys() and 'component' in data.keys():
                    try:
                        adaptThread(data['component'], data['parameter'], data['expression'])
                    except:
                        _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                        pass
                if 'isThreadLength' in data.keys() and 'component' in data.keys():
                    try:
                        adaptThreadLength(data['component'], data['parameter'], data['expression'])
                    except:
                        pass

                args.returnData = str({'expression': param.expression})
            if 'jointOriginSelection' in data.keys() and 'jointOrigin' in data.keys():
                try:
                    createJoins(data['jointOrigin'], data['jointOriginSelection'])
                except:
                    pass
                args.returnData = str(data)

            if 'deleteJoint' in data.keys() and 'deleteComponents' in data.keys():
                try:
                    deleteJoints(data['deleteJoint'], data['deleteComponents'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'getRootName' in data.keys():
                name = ""
                try:
                    name = getRootName()
                except:
                    pass
                args.returnData = str({'name': name})

            if 'newJoints' in data.keys():
                try:
                    newJoints(data['newJoints'])
                except:
                    pass
                args.returnData = str(data)
            if 'newJointsByOccurrences' in data.keys():
                try:
                    newJointsByOccurrences(data['newJointsByOccurrences'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'highlightOccurrencesByComponentName' in data.keys():
                try:
                    highlightOccurrencesByComponentName(data['highlightOccurrencesByComponentName'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'highlightJointByName' in data.keys():
                try:
                    highlightJointByName(data['highlightJointByName'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'createInputSelections' in data.keys():
                try:
                    createInputSelections()
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'getMaterials' in data.keys():
                result = getMaterials()
                args.returnData = str(result)
            if 'setMaterial' in data.keys() and 'name' in data.keys() and 'materialId' in data.keys() and 'materialLibraryId' in data.keys():
                try:
                    result = setMaterial(data['name'], data['materialLibraryId'], data['materialId'])
                except:
                    pass
                args.returnData = str({"setMaterial": "jio"})
        except:
            pass
            #_ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


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
        panel = _ui.allToolbarPanels.itemById('InsertPanel') #SolidScriptsAddinsPanel
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
        panel = _ui.allToolbarPanels.itemById('InsertPanel')
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

        #_ui.messageBox('Stop addin')
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
