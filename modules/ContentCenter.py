import inspect
import json
import math
import os
import platform
import subprocess
import sys

import adsk.cam
import adsk.core
import adsk.fusion
import traceback

_script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
_script_dir = os.path.dirname(_script_path)
_module_dir = os.path.abspath(os.path.join(_script_dir, "modules"))
sys.path.append(_module_dir)

try:
    import requests
except:
    pass

# global set of event handlers to keep them referenced for the duration of the command
handlers = []
_handlers = []
_app = adsk.core.Application.cast(None)
_ui = adsk.core.UserInterface.cast(None)
_num = 0
_host = "http://localhost:3000"  # "https://custom.hk-fs.de"
_last_imported = None
_component_stack = []
_timeline_group_stack = []
_parameter_stack = []
_occurrences = []
_joint_origins = []
_id_stack = []
_use_new_browser = True

_is_mac_os = False

# checks if OS is MacOS
if platform.system() == 'Darwin':
    _is_mac_os = True


def initialize():
    global _num, _last_imported, _component_stack, _timeline_group_stack, _parameter_stack, _occurrences, \
        _joint_origins, _id_stack
    _num = 0
    _last_imported = None
    _component_stack = []
    _timeline_group_stack = []
    _parameter_stack = []
    _occurrences = []
    _joint_origins = []
    _id_stack = []


def _set_material(component_name, material_library_id, material_id):
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    component = design.allComponents.itemByName(component_name)
    material = _app.materialLibraries.item(material_library_id).materials.item(material_id)
    component.material = material
    return {"setMaterial": True}


def _get_materials():
    data = []
    for index, material_library in enumerate(_app.materialLibraries):
        material_lib_dict = {'label': material_library.name, 'value': index}
        materials = []
        for j_index, material in enumerate(material_library.materials):
            material_dict = {'value': j_index, 'label': material.name}
            materials.append(material_dict)
        material_lib_dict['materials'] = materials
        data.append(material_lib_dict)
    return data


def _get_all_joint_origins():
    global _joint_origins
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)
    _joint_origins = []
    for item in design.allComponents:
        joint = {"component": item.name, "names": []}
        for index, jointOrigin in enumerate(item.jointOrigins):
            joint['names'].append(jointOrigin.name)
        _joint_origins.append(joint)
    return _joint_origins


def _get_all_joints():
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)
    joints = []
    for item in design.allComponents:
        components_joints = {"component": item.name, "joints": []}
        for index, joint in enumerate(item.joints):
            new_joint = {'name': joint.name, 'isFlipped': joint.isFlipped}

            if joint.jointMotion:
                new_joint['jointMotion'] = joint.jointMotion.jointType
            if joint.occurrenceOne:
                new_joint['occurrenceOne'] = joint.occurrenceOne.name
            if joint.occurrenceTwo:
                new_joint['occurrenceTwo'] = joint.occurrenceTwo.name
            components_joints['joints'].append(new_joint)
        joints.append(components_joints)
    return json.dumps({"joints": joints})


def _get_component_index(parameter):
    global _parameter_stack
    # find component index by parameter name
    for index, parameter_array in enumerate(_parameter_stack):
        for parameter_dict in parameter_array:
            if 'name' in parameter_dict and parameter == parameter_dict['name']:
                return index
    return -1


def _get_root_name():
    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    root_comp = design.rootComponent
    return root_comp.name


def _compare_origins(first_origin, second_origin):
    # ui.messageBox(str(firstVertex.geometry.x) + " " + str(firstVertex.geometry.y) + \
    # " " + str(firstVertex.geometry.z) + "\n" + str(secondVertex.geometry.x) + " " + \
    # str(secondVertex.geometry.y) + " " + str(secondVertex.geometry.z))
    if math.isclose(first_origin.x, second_origin.x) \
            and math.isclose(first_origin.y, second_origin.y) \
            and math.isclose(first_origin.z, second_origin.z):
        return True
    return False


def _joint_exists(joints, occurrence_one, occurrences_two, joint_origin_name_one, joint_origin_name_two):
    # Get active design
    global _app, _ui
    _app = adsk.core.Application.get()
    _ui = _app.userInterface
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    root_comp = design.rootComponent
    is_root = False
    if occurrence_one.name == root_comp.name:
        is_root = True

    # progressDialog.reset()
    # progressDialog.title = str(' ' + occurrenceOne.name + '.' + jointOriginNameOne + ' - ' + jointOriginNameTwo)
    # progressDialog.maximumValue = progressDialog.maximumValue + occurrencesTwo.count

    # index = 0
    # progressDialog.progressValue = index

    # get all joint name tuples where occurrenceOne was used
    joint_dicts = []
    for joint in joints:
        occurrence_one_name = joint.occurrenceOne.name
        if joint.occurrenceTwo:
            occurrence_two_name = joint.occurrenceTwo.name
        else:
            occurrence_two_name = None
        if occurrence_one_name == occurrence_one.name or occurrence_two_name == occurrence_one.name:
            joint_dict = {"one": occurrence_one_name, "two": occurrence_two_name, "joint": joint}
            joint_dicts.append(joint_dict)

    # _ui.messageBox(str(joint_dicts))

    for occurrenceTwo in occurrences_two:
        # index += 1
        # progressDialog.progressValue = progressDialog.progressValue + 1
        for joint_dict in joint_dicts:
            if joint_dict["one"] == occurrence_one.name and joint_dict["two"] == occurrenceTwo.name or \
                    joint_dict["two"] == occurrence_one.name and joint_dict["one"] == occurrenceTwo.name:
                # _ui.messageBox("exists")
                joint = joint_dict["joint"]
                if joint.geometryOrOriginOne.objectType == adsk.fusion.JointGeometry.classType() \
                        and joint.geometryOrOriginTwo.objectType == adsk.fusion.JointGeometry.classType() \
                        and occurrenceTwo.name == joint.occurrenceOne.name or is_root:
                    if is_root:
                        one = occurrence_one.jointOrigins.itemByName(joint_origin_name_one).geometry.origin
                    else:
                        one = occurrence_one.component.jointOrigins.itemByName(
                            joint_origin_name_one).createForAssemblyContext(occurrence_one).geometry.origin
                    two = joint.geometryOrOriginTwo.origin
                    three = joint.geometryOrOriginOne.origin
                    four = occurrenceTwo.component.jointOrigins.itemByName(
                        joint_origin_name_two).createForAssemblyContext(
                        occurrenceTwo).geometry.origin

                    if _compare_origins(one, three) and _compare_origins(two, four) or \
                            _compare_origins(one, two) and _compare_origins(three, four):
                        # _ui.messageBox("yes")
                        # progressDialog.maximumValue = progressDialog.maximumValue - index
                        return True
    return False


def _new_joints(new_joints):
    joint_origin_dict_one = new_joints['jointOrigin']
    joint_origin_list = new_joints['jointOriginList']

    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    root_comp = design.rootComponent
    joints = root_comp.joints

    # get both components
    component_one = design.allComponents.itemByName(joint_origin_dict_one['component'])

    # get occurrences of each component
    occurrences_one = root_comp.occurrencesByComponent(component_one)

    # start_time = time.time()

    progress_dialog = _ui.createProgressDialog()
    progress_dialog.isBackgroundTranslucent = False
    progress_len = len(joint_origin_list) + 2
    progress_dialog.show(str('Dupe ' + component_one.name), 'Percentage: %p, Current Value: %v, Total steps: %m', 0,
                         progress_len)

    i = 2
    progress_dialog.progressValue = 1
    progress_dialog.progressValue = 2

    # print("--- %s seconds ---" % (time.time() - start_time))

    for jointOriginDictTwo in joint_origin_list:

        component_two = design.allComponents.itemByName(jointOriginDictTwo['component'])
        occurrences_two = root_comp.occurrencesByComponent(component_two)

        if component_two.name == root_comp.name:
            has_joint = _joint_exists(joints, component_two, occurrences_one, jointOriginDictTwo['name'],
                                      joint_origin_dict_one['name'])
            # progress_dialog.reset()
            # progress_dialog.maximumValue = progress_len
            # progress_dialog.progressValue = i
            if not has_joint:
                # make a new copy
                if root_comp.occurrences.count == 1 and root_comp.occurrences[0].joints.count < 1:
                    # join the first element
                    new_occurrence = root_comp.occurrences.item(0)
                else:
                    # make a new copy
                    new_occurrence = root_comp.occurrences.addExistingComponent(component_one,
                                                                                adsk.core.Matrix3D.create())

                joint_input = joints.createInput(new_occurrence.component.jointOrigins.itemByName(
                    joint_origin_dict_one['name']).createForAssemblyContext(new_occurrence),
                                                 component_two.jointOrigins.itemByName(jointOriginDictTwo['name']))

                # Set the joint input
                angle = adsk.core.ValueInput.createByString('0 deg')
                joint_input.angle = angle
                offset = adsk.core.ValueInput.createByString('0 cm')
                joint_input.offset = offset
                joint_input.setAsRigidJointMotion()

                # Create the joint
                joint = joints.add(joint_input)
        else:
            progress_dialog.maximumValue = progress_dialog.maximumValue + len(occurrences_one)
            # jointsTemp = []
            root_occurrences = root_comp.occurrences
            matrix = adsk.core.Matrix3D.create()

            # p = mp.Pool(4)
            # p.map(partial(addOccurrence, joints=joints, occurrences_two=occurrences_two, joint_origin_dict_one=joint_origin_dict_one, jointOriginDictTwo=jointOriginDictTwo, component_two=component_two, matrix=matrix, component_one=component_one, root_occurrences=root_occurrences), occurrences_one) # range(0,1000) if you want to replicate your example
            # p.close()
            # p.join()
            for occurrenceOne in occurrences_one:
                # i += 1
                progress_dialog.progressValue = progress_dialog.progressValue + 1
                # check occurrences for each component if joint already exists
                # if occurenceOne already have an existing joint between both components skip it
                has_joint = _joint_exists(joints, occurrenceOne, occurrences_two, joint_origin_dict_one['name'],
                                          jointOriginDictTwo['name'])

                if not has_joint:
                    # make a new copy
                    # print("copy start --- %s seconds ---" % (time.time() - start_time))
                    all_occurrences = root_comp.allOccurrencesByComponent(component_two)
                    if all_occurrences.count == 1 and all_occurrences.item(0).joints.count < 1:
                        # join the first element
                        new_occurrence = all_occurrences.item(0)
                    else:
                        # make a new copy
                        new_occurrence = root_occurrences.addExistingComponent(component_two, matrix)
                    # print("copy stop --- %s seconds ---" % (time.time() - start_time))

                    joint_input = joints.createInput(new_occurrence.component.jointOrigins.itemByName(
                        jointOriginDictTwo['name']).createForAssemblyContext(new_occurrence),
                                                     component_one.jointOrigins.itemByName(
                                                         joint_origin_dict_one['name']).createForAssemblyContext(
                                                         occurrenceOne))

                    # Set the joint input
                    angle = adsk.core.ValueInput.createByString('0 deg')
                    joint_input.angle = angle
                    offset = adsk.core.ValueInput.createByString('0 cm')
                    joint_input.offset = offset
                    joint_input.setAsRigidJointMotion()

                    joints.add(joint_input)
            # addOccurrence(occurrenceOne, joints, occurrences_two, joint_origin_dict_one, jointOriginDictTwo, component_two, matrix, component_one, root_occurrences)
            # threading.Thread(target = addOccurrence, args = (occurrenceOne, joints, occurrences_two, joint_origin_dict_one, jointOriginDictTwo, component_two, matrix, component_one, root_occurrences)).start()
            # for joint_input in jointsTemp:
            #    joints.add(joint_input)
            # print("e --- %s seconds ---" % (time.time() - start_time))
        i += 1
        progress_dialog.progressValue = i
    progress_dialog.hide()
    # design.timeline.moveToEnd()
    '''
    for occurrenceTwo in occurrences_two:
        has_joint = jointExists(joints, occurrenceTwo, occurrences_one, jointOriginDictTwo['name'], joint_origin_dict_one['name'])

        if not has_joint:
            # make a new copy
            new_occurrence = root_comp.occurrences.addExistingComponent(component_one, adsk.core.Matrix3D.create())

            joint_input = joints.createInput(new_occurrence.component.jointOrigins.itemByName(joint_origin_dict_one['name']).createForAssemblyContext(new_occurrence), component_two.jointOrigins.itemByName(jointOriginDictTwo['name']).createForAssemblyContext(occurrenceTwo))

            # Set the joint input
            angle = adsk.core.ValueInput.createByString('0 deg')
            joint_input.angle = angle
            offset = adsk.core.ValueInput.createByString('0 cm')
            joint_input.offset = offset
            joint_input.setAsRigidJointMotion()

            #Create the joint
            joint = joints.add(joint_input)'''


def _new_joints_by_occurrences(new_joints):
    joint_origin_dict_one = new_joints['jointOrigin']
    joint_origin_list = new_joints['jointOriginList']

    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    root_comp = design.rootComponent
    joints = root_comp.joints

    # get both components
    component_one = design.allComponents.itemByName(joint_origin_dict_one['component'])

    progress_dialog = _ui.createProgressDialog()
    progress_dialog.isBackgroundTranslucent = False
    progress_len = len(joint_origin_list)
    progress_dialog.show(str('Dupe ' + component_one.name), 'Percentage: %p, Current Value: %v, Total steps: %m', 0,
                         progress_len)

    i = 0

    for jointOriginDictTwo in joint_origin_list:
        if jointOriginDictTwo['component'] == root_comp.name:
            jointOriginDictTwo['occurrence'] = root_comp.name
            component_two = root_comp
        else:
            occurrence_two = root_comp.allOccurrences.itemByName(jointOriginDictTwo['occurrence'])
            component_two = occurrence_two.component
        if jointOriginDictTwo['occurrence']:
            # occurrencesTwo = root_comp.occurrencesByComponent(component_two)

            if jointOriginDictTwo['component'] == root_comp.name:
                # use also first element to create joints
                if root_comp.occurrences.count == 1 and root_comp.occurrences[0].joints.count < 1:
                    # join the first element
                    new_occurrence = root_comp.occurrences.item(0)
                else:
                    # make a new copy
                    new_occurrence = root_comp.occurrences.addExistingComponent(component_one,
                                                                                adsk.core.Matrix3D.create())

                jointInput = joints.createInput(new_occurrence.component.jointOrigins.itemByName(
                    joint_origin_dict_one['name']).createForAssemblyContext(new_occurrence),
                                                component_two.jointOrigins.itemByName(jointOriginDictTwo['name']))

                # Set the joint input
                angle = adsk.core.ValueInput.createByString('0 deg')
                jointInput.angle = angle
                offset = adsk.core.ValueInput.createByString('0 cm')
                jointInput.offset = offset
                jointInput.setAsRigidJointMotion()

                # Create the joint
                joint = joints.add(jointInput)
            else:
                # use also first element to create joints
                # _ui.messageBox(str(component_one.occurrences.count) + " " + str(component_one.name) + str() );
                all_occurrences = root_comp.allOccurrencesByComponent(component_one)
                if all_occurrences.count == 1 and all_occurrences.item(0).joints.count < 1:
                    # join the first element
                    new_occurrence = all_occurrences.item(0)
                else:
                    # make a new copy
                    new_occurrence = root_comp.occurrences.addExistingComponent(component_one,
                                                                                adsk.core.Matrix3D.create())

                jointInput = joints.createInput(new_occurrence.component.jointOrigins.itemByName(
                    joint_origin_dict_one['name']).createForAssemblyContext(new_occurrence),
                                                component_two.jointOrigins.itemByName(
                                                    jointOriginDictTwo['name']).createForAssemblyContext(
                                                    occurrence_two))

                # Set the joint input
                angle = adsk.core.ValueInput.createByString('0 deg')
                jointInput.angle = angle
                offset = adsk.core.ValueInput.createByString('0 cm')
                jointInput.offset = offset
                jointInput.setAsRigidJointMotion()

                # Create the joint
                joint = joints.add(jointInput)
        i += 1
        progress_dialog.progressValue = i
    progress_dialog.hide()


def _delete_joints(delete_joint, delete_components):
    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component in this design
    root_comp = design.rootComponent
    joints = root_comp.joints

    component = joints.itemByName(delete_joint).occurrenceOne.component
    # componentTwo = joints.itemByName(deleteJoint).occurrenceOne.component
    l = list(root_comp.allOccurrencesByComponent(component))
    # lTwo = list(root_comp.allOccurrencesByComponent(componentTwo))
    if delete_components:
        progress_dialog = _ui.createProgressDialog()
        progress_dialog.isBackgroundTranslucent = False
        progress_len = len(l)
        progress_dialog.show(str('Delete ' + component.name), 'Percentage: %p, Current Value: %v, Total steps: %m', 0,
                             progress_len)

        for index, occurrence in enumerate(l):
            if not index < 1:
                try:
                    occurrence.timelineObject.rollTo(False)
                except:
                    pass
                occurrence.deleteMe()
                progress_dialog.progressValue = index
        design.timeline.moveToEnd()
        # for index, occurrence in enumerate(lTwo):
        #     if not index < 1:
        #         occurrence.deleteMe()
        progress_dialog.hide()

    else:
        occurrence = joints.itemByName(delete_joint).occurrenceOne
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


def _highlight_occurrence(occurrence_one, color=(50, 180, 10, 255)):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent

    # Create the color effect.
    r, g, b, a = color
    red_color = adsk.core.Color.create(r, g, b, a)
    solid_color = adsk.fusion.CustomGraphicsSolidColorEffect.create(red_color)

    tx = occurrence_one.boundingBox.minPoint.x + abs(
        occurrence_one.boundingBox.minPoint.x - occurrence_one.boundingBox.maxPoint.x)
    ty = occurrence_one.boundingBox.minPoint.y
    sx = occurrence_one.boundingBox.minPoint.x
    sy = occurrence_one.boundingBox.minPoint.y + abs(
        occurrence_one.boundingBox.minPoint.y - occurrence_one.boundingBox.maxPoint.y)

    coord_array = [occurrence_one.boundingBox.minPoint.x, occurrence_one.boundingBox.minPoint.y,
                   occurrence_one.boundingBox.minPoint.z,
                   occurrence_one.boundingBox.minPoint.x, occurrence_one.boundingBox.minPoint.y,
                   occurrence_one.boundingBox.maxPoint.z,
                   sx, sy, occurrence_one.boundingBox.maxPoint.z,
                   sx, sy, occurrence_one.boundingBox.minPoint.z,
                   tx, ty, occurrence_one.boundingBox.maxPoint.z,
                   tx, ty, occurrence_one.boundingBox.minPoint.z,
                   occurrence_one.boundingBox.maxPoint.x, occurrence_one.boundingBox.maxPoint.y,
                   occurrence_one.boundingBox.minPoint.z,
                   occurrence_one.boundingBox.maxPoint.x, occurrence_one.boundingBox.maxPoint.y,
                   occurrence_one.boundingBox.maxPoint.z]
    coords = adsk.fusion.CustomGraphicsCoordinates.create(coord_array)

    # Create a graphics group on the root component.
    graphics = root.customGraphicsGroups.add()

    # Create the graphics body.
    line_indices = [0, 1, 0, 3, 0, 5, 1, 2, 2, 7, 3, 6, 6, 7, 6, 5, 4, 5, 4, 7, 4, 1, 3, 2]  #
    lines = graphics.addLines(coords, line_indices, False)
    lines.weight = 2
    lines.color = solid_color
    text_matrix = adsk.core.Matrix3D.create()

    text_matrix.setToAlignCoordinateSystems(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(1, 0, 0),
                                            adsk.core.Vector3D.create(0, 1, 0), adsk.core.Vector3D.create(0, 0, 1),
                                            adsk.core.Point3D.create(occurrence_one.boundingBox.minPoint.x,
                                                                     occurrence_one.boundingBox.minPoint.y,
                                                                     occurrence_one.boundingBox.maxPoint.z),
                                            adsk.core.Vector3D.create(0, 1, 0),
                                            adsk.core.Vector3D.create(0, 0, 1), adsk.core.Vector3D.create(1, 0, 0))

    text = graphics.addText(occurrence_one.name, "Calibri",
                            abs(occurrence_one.boundingBox.minPoint.x - occurrence_one.boundingBox.maxPoint.x) \
                            * 2 / len(occurrence_one.name),
                            text_matrix)
    text.color = solid_color

    # Refresh the graphics.
    _app.activeViewport.refresh()


def _highlight_joint_by_name(joint_name):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent

    joints = root.joints

    occurrence = joints.itemByName(joint_name).occurrenceOne
    occurrence_two = joints.itemByName(joint_name).occurrenceTwo

    for item in list(root.customGraphicsGroups):
        item.deleteMe()

    _app.activeViewport.refresh()

    if occurrence_two:
        _highlight_occurrence(occurrence_two, color=(200, 50, 10, 255))
    else:
        _highlight_occurrence(joints.itemByName(joint_name).parentComponent, color=(200, 50, 10, 255))

    _highlight_occurrence(occurrence)


def _highlight_occurrences_by_component_name(component_name):
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent

    for item in list(root.customGraphicsGroups):
        item.deleteMe()

    _app.activeViewport.refresh()

    if component_name == root.name:
        _highlight_occurrence(root, color=(200, 50, 10, 255))
    else:
        # get both components
        component_one = design.allComponents.itemByName(component_name)

        # get occurrences of each component
        occurrences_one = root.occurrencesByComponent(component_one)

        for occurrenceOne in occurrences_one:
            _highlight_occurrence(occurrenceOne)


def _remove_highlight_all():
    design = adsk.fusion.Design.cast(_app.activeProduct)
    root = design.rootComponent

    # delete all custom graphics
    for item in list(root.customGraphicsGroups):
        item.deleteMe()

    # Refresh the graphics.
    _app.activeViewport.refresh()


def _adapt_thread(component_name, parameter, thread_expression):
    # get the design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    thread_size = design.unitsManager.evaluateExpression(thread_expression)

    # get the root component of the active design.
    component = design.allComponents.itemByName(component_name)

    # return if component not found
    if not component:
        return

    # iterate through all timeline groups and expand them to work on the thread
    for item in design.timeline.timelineGroups:
        item.isCollapsed = False

    thread_features = component.features.threadFeatures

    # get thread
    if thread_features.count < 1:
        return
    thread = thread_features.item(thread_features.count - 1)
    # threadLocation = thread.threadLocation

    is_internal = thread.threadInfo.isInternal

    # query the thread table to get the thread information
    thread_data_query = thread_features.threadDataQuery
    default_thread_type = thread_data_query.defaultMetricThreadType
    recommend_data = thread_data_query.recommendThreadData(thread_size, is_internal, default_thread_type)

    # create the thread_info according to the query result
    if recommend_data[0]:
        thread_info = thread_features.createThreadInfo(is_internal, default_thread_type, recommend_data[1],
                                                       recommend_data[2])
        # roll before thread to change
        thread.timelineObject.rollTo(True)
        if thread.threadLength:
            thread_length = thread.threadLength.expression
        else:
            thread_length = None
        is_full_length = thread.isFullLength

        # try to set the new thread_info
        try:
            # set the thread length to smallest possible thread_length to prevent invalid thread length error
            if thread.threadOffset:
                thread.setThreadOffsetLength(adsk.core.ValueInput.createByString(thread.threadOffset.expression),
                                             adsk.core.ValueInput.createByString("0.0000000001"), thread.threadLocation)
            else:
                thread.setThreadOffsetLength(adsk.core.ValueInput.createByString("0"),
                                             adsk.core.ValueInput.createByString("0.0000000001"), thread.threadLocation)

            # set thread_info
            thread.threadInfo = thread_info

            # set previous thread_size
            if is_full_length:
                thread.isFullLength = is_full_length
            elif thread.threadOffset and thread_length:
                print(str(thread_length))
                thread.setThreadOffsetLength(adsk.core.ValueInput.createByString(thread.threadOffset.expression),
                                             adsk.core.ValueInput.createByString(thread_length), thread.threadLocation)
            elif thread_length:
                thread.setThreadOffsetLength(adsk.core.ValueInput.createByString("0"),
                                             adsk.core.ValueInput.createByString(thread_length), thread.threadLocation)
        except:
            print('Failed:\n{}'.format(traceback.format_exc()))
            pass
        # if thread.healthState > 0:
        #    print(str(thread.healthState))
        design.timeline.moveToEnd()
        # print(str(thread.healthState))


def _adapt_thread_length(component_name, parameter, thread_expression):
    # get the design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # threadLength = design.unitsManager.evaluateExpression(threadExpression)

    # get the root component of the active design.
    component = design.allComponents.itemByName(component_name)

    # return if component not found
    if not component:
        return

    # iterate through all timeline groups and expand them to work on the thread
    for item in design.timeline.timelineGroups:
        item.isCollapsed = False

    thread_features = component.features.threadFeatures

    # get thread
    thread = thread_features.item(thread_features.count - 1)
    # threadLocation = thread.threadLocation

    thread.timelineObject.rollTo(True)
    thread.setThreadOffsetLength(adsk.core.ValueInput.createByString(thread.threadOffset.expression),
                                 adsk.core.ValueInput.createByString(thread_expression + " -0.0000000001"),
                                 thread.threadLocation)
    design.timeline.moveToEnd()


def _insert_content(id, name, url):
    global _last_imported, _component_stack, _timeline_group_stack, _parameter_stack, _is_mac_os, _script_dir
    des = adsk.fusion.Design.cast(_app.activeProduct)

    previous_params = des.userParameters
    previous_params_str = []
    for u in des.userParameters:
        previous_params_str.append(u.name)

    import_manager = _app.importManager

    # Get active design
    product = _app.activeProduct
    design = adsk.fusion.Design.cast(product)

    # Get root component
    root_comp = design.rootComponent

    # save previous names of components
    previous_component_names = []
    for item in design.allComponents:
        previous_component_names.append(item.name)
    previous_group_names = []
    for item in design.timeline.timelineGroups:
        previous_group_names.append(item.name)

    download_dir = os.path.join(_script_dir, 'downloads')
    os.makedirs(download_dir, exist_ok=True)

    keep_characters = (' ', '.', '_')
    archive_file_name_un = name + '.f3d'  # url[url.rfind("/")+1:]
    archive_file_name = os.path.join(download_dir,
                                     "".join(c for c in archive_file_name_un if
                                             c.isalnum() or c in keep_characters).rstrip())
    if _is_mac_os:
        subprocess.call(['curl', '-o', archive_file_name, '-L', url])
    else:
        r = requests.get(url, allow_redirects=True)
        open(archive_file_name, 'wb').write(r.content)

    archive_options = import_manager.createFusionArchiveImportOptions(archive_file_name)
    # Import archive file to root component
    imported = import_manager.importToTarget2(archive_options, root_comp)
    _last_imported = imported

    # save current names of components
    component_names = []
    for item in design.allComponents:
        component_names.append(item.name)
    group_names = []
    for item in design.timeline.timelineGroups:
        group_names.append(item.name)

    # compare previous and current to get the inserted component
    added_component_names = list(set(component_names) - set(previous_component_names))
    added_group_names = list(set(group_names) - set(previous_group_names))

    for component in added_component_names:
        _component_stack.append(component)
    for group in added_group_names:
        _timeline_group_stack.append(group)

    # des.userParameters.add("contentCenterID", adsk.core.ValueInput.createByString("0"), "", str(id))

    params = des.userParameters
    params_str = []
    for u in des.userParameters:
        params_str.append(u.name)

    new_parameters = list(set(params_str) - set(previous_params_str))
    parameters = []
    for parameter in new_parameters:
        des.userParameters.itemByName(parameter).comment = str(id)
        param = des.userParameters.itemByName(parameter)
        dict = {'name': parameter, 'expression': param.expression, 'comment': param.comment}
        parameters.append(dict)

    _parameter_stack.append(parameters)

    component = design.allComponents.itemByName(_component_stack[-1])
    joint_origin_names = []
    for index, jointOrigin in enumerate(component.allJointOrigins):
        joint_origin_names.append(jointOrigin.name)
    joint_origins = []
    joint_origins.append({"component": component.name, "names": joint_origin_names, "selectedPresets": []})

    return {"name": _component_stack[-1], "parameters": parameters, "jointOrigins": joint_origins}


def _find(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1


def _get_parameters():
    design = _app.activeProduct
    user_parameters = []

    for param in design.userParameters:
        user_parameter = {'name': param.name, 'expression': param.expression, 'comment': param.comment}
        user_parameters.append(user_parameter)
    return json.dumps({'parameters': user_parameters})


def _get_user_parameters():
    global _app
    design = _app.activeProduct

    component_names = []
    model_param_names = []
    user_param_names = []

    document_name = design.parentDocument.name

    for component in design.allComponents:
        if component.parentDesign.parentDocument.name == document_name:
            component_names.append(component.name)

            # getting all parameter names for every component
            model_names = []
            try:
                for model in component.modelParameters:
                    model_names.append(model.name)
                model_param_names.append(model_names)
            except:
                model_param_names.append([])
                pass

    for userParam in design.userParameters:
        for param in userParam.dependentParameters:
            name = param.name
            for i, model_names in enumerate(model_param_names):
                if name in model_names:
                    index = _find(user_param_names, 'component', component_names[i])
                    if index > -1:
                        k = _find(user_param_names[index]['parameters'], 'name', userParam.name)
                        if not k > -1:
                            user_param_names[index]['parameters'].append(
                                {"name": userParam.name, "expression": userParam.expression,
                                 "comment": userParam.comment})
                    else:
                        d = {'component': component_names[i], 'parameters': [
                            {"name": userParam.name, "expression": userParam.expression, "comment": userParam.comment}]}
                        user_param_names.append(d)

    return json.dumps({'userParameters': user_param_names})


def _create_input_selections():
    try:
        global _app, _ui, _str_input, _handlers
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        cmd_def = _ui.commandDefinitions.itemById('cmdInputSelections')
        if not cmd_def:
            cmd_def = _ui.commandDefinitions.addButtonDefinition('cmdInputSelections', 'Select Inputs for Joints',
                                                                 'Sample to demonstrate various command inputs.')

            # Connect to the command created event.
            on_command_created = SelectionCreatedHandler()
            cmd_def.commandCreated.add(on_command_created)
            _handlers.append(on_command_created)

            # Execute the command definition.
            cmd_def.execute()
        else:
            try:
                cmd_def.deleteMe()
            except:
                pass

        # Prevent this module from being terminated when the script returns, because we are waiting for event handlers to fire.
        # adsk.autoTerminate(False)
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler that reacts to any changes the user makes to any of the command inputs.
class SelectionInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _str_input
        try:
            event_args = adsk.core.InputChangedEventArgs.cast(args)
            inputs = event_args.inputs
            cmd_input = event_args.input

            if cmd_input.id == 'selection':
                selectionInput = inputs.itemById('selection')

        except:
            _ui().messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler that reacts to any changes the user makes to any of the command inputs.
class SelectionExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _str_input
        try:
            event_args = adsk.core.CommandEventArgs.cast(args)

            # Code to react to the event.
            app = adsk.core.Application.get()
            ui = app.userInterface

            command = args.firingEvent.sender
            inputs = command.commandInputs

            for input in inputs:
                if input.id == 'selection':
                    selection_input = inputs.itemById('selection')

            list = []
            for i in range(selection_input.selectionCount):
                dict = {}
                if selection_input.selection(i).entity:
                    dict['objectType'] = selection_input.selection(i).entity.objectType
                    dict['name'] = selection_input.selection(i).entity.name
                    if selection_input.selection(i).entity.parentComponent:
                        dict['component'] = selection_input.selection(i).entity.parentComponent.name
                    if selection_input.selection(i).entity.assemblyContext:
                        dict['occurrence'] = selection_input.selection(i).entity.assemblyContext.name
                list.append(dict)
            # ui.messageBox(str(list))

            palette = _ui.palettes.itemById('myPalette')
            if palette:
                palette.sendInfoToHTML('send', str({"inputSelections": list}))

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
            # adsk.terminate()
            # Get the existing command definition or create it if it doesn't already exist.
            cmd_def = _ui.commandDefinitions.itemById('cmdInputSelections')
            cmd_def.deleteMe()
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
            on_destroy = SelectionDestroyHandler()
            cmd.destroy.add(on_destroy)
            _handlers.append(on_destroy)

            # Connect to the input changed event.
            on_input_changed = SelectionInputChangedHandler()
            cmd.inputChanged.add(on_input_changed)
            _handlers.append(on_input_changed)

            # Connect to the execute event.
            on_execute = SelectionExecuteHandler()
            cmd.execute.add(on_execute)
            _handlers.append(on_execute)

            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs

            # create a selection input.
            selection_input = inputs.addSelectionInput('selection', 'Select', 'Basic select command input')
            selection_input.addSelectionFilter("JointOrigins")
            # selection_input.addSelectionFilter("Vertices")
            # selection_input.addSelectionFilter("SketchCurves")
            # selection_input.addSelectionFilter("SketchPoints")
            selection_input.setSelectionLimits(0)

        except:
            _ui().messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler for the commandExecuted event.
class ShowPaletteCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        global _use_new_browser
        try:
            # Create and display the palette.
            palette = _ui.palettes.itemById('myPalette')
            if not palette:
                palette = _ui.palettes.add('myPalette', 'Content Center', _host, True, True, True, 1000,
                                           1000, _use_new_browser)  # ./palette/build/index.html

                # Dock the palette to the right side of Fusion window.
                palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateRight

                # Add handler to HTMLEvent of the palette.
                on_html_event = MyHTMLEventHandler()
                palette.incomingFromHTML.add(on_html_event)
                handlers.append(on_html_event)

                # Add handler to CloseEvent of the palette.
                on_closed = MyCloseEventHandler()
                palette.closed.add(on_closed)
                handlers.append(on_closed)
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
            on_execute = ShowPaletteCommandExecuteHandler()
            command.execute.add(on_execute)
            handlers.append(on_execute)
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
                global _num
                _num += 1
                palette.sendInfoToHTML('send', str({"id": 1, "parameters": _num}))
        except:
            _ui.messageBox('Command executed failed: {}'.format(traceback.format_exc()))


# Event handler for the commandCreated event.
class SendInfoCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            command = args.command
            on_execute = SendInfoCommandExecuteHandler()
            command.execute.add(on_execute)
            handlers.append(on_execute)
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler for the palette close event.
class MyCloseEventHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            return
            # _ui.messageBox('Close button is clicked.')
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


# Event handler for the palette HTML event.
class MyHTMLEventHandler(adsk.core.HTMLEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            html_args = adsk.core.HTMLEventArgs.cast(args)
            data = json.loads(html_args.data)
            if 'id' in data.keys() and 'name' in data.keys():
                path = _host + data['url']
                try:
                    res_input = _insert_content(data['id'], data['name'], path)
                    _id_stack.append(data["id"])
                except:
                    pass
                args.returnData = str(
                    {"id": data['id'], "name": res_input['name'], 'parameters': res_input['parameters'],
                     'jointOrigins': res_input['jointOrigins']})

            if 'getJointOrigins' in data.keys():
                initialize()
                joint_origins = _get_all_joint_origins()
                args.returnData = str({'jointOrigins': joint_origins})

            if 'getJoints' in data.keys():
                initialize()
                joints = _get_all_joints()
                args.returnData = str(joints)

            if 'getParameters' in data.keys():
                try:
                    parameters = _get_user_parameters()  # old getParameters()
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
                        _adapt_thread(data['component'], data['parameter'], data['expression'])
                    except:
                        _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                        pass
                if 'isThreadLength' in data.keys() and 'component' in data.keys():
                    try:
                        _adapt_thread_length(data['component'], data['parameter'], data['expression'])
                    except:
                        pass

                args.returnData = str({'expression': param.expression})
            if 'jointOriginSelection' in data.keys() and 'jointOrigin' in data.keys():
                # try:
                #     method createJoints is missing
                #     createJoints(data['jointOrigin'], data['jointOriginSelection'])
                # except:
                #     pass
                args.returnData = str(data)

            if 'deleteJoint' in data.keys() and 'deleteComponents' in data.keys():
                try:
                    _delete_joints(data['deleteJoint'], data['deleteComponents'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'getRootName' in data.keys():
                name = ""
                try:
                    name = _get_root_name()
                except:
                    pass
                args.returnData = str({'name': name})

            if 'newJoints' in data.keys():
                try:
                    _new_joints(data['newJoints'])
                except:
                    pass
                args.returnData = str(data)
            if 'newJointsByOccurrences' in data.keys():
                try:
                    _new_joints_by_occurrences(data['newJointsByOccurrences'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'highlightOccurrencesByComponentName' in data.keys():
                try:
                    _highlight_occurrences_by_component_name(data['highlightOccurrencesByComponentName'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'highlightJointByName' in data.keys():
                try:
                    _highlight_joint_by_name(data['highlightJointByName'])
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'unlightAll' in data.keys():
                try:
                    _remove_highlight_all()
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'createInputSelections' in data.keys():
                try:
                    _create_input_selections()
                except:
                    pass
                args.returnData = str(json.dumps(data))

            if 'getMaterials' in data.keys():
                result = _get_materials()
                args.returnData = str(result)
            if 'setMaterial' in data.keys() and \
                    'name' in data.keys() and \
                    'materialId' in data.keys() and \
                    'materialLibraryId' in data.keys():
                try:
                    result = _set_material(data['name'], data['materialLibraryId'], data['materialId'])
                except:
                    pass
                args.returnData = str({"setMaterial": "jio"})
        except:
            pass
            # _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:
        global _ui, _app
        _app = adsk.core.Application.get()
        _ui = _app.userInterface

        # Add a command that displays the panel.
        show_palette_cmd_def = _ui.commandDefinitions.itemById('showPalette')
        if not show_palette_cmd_def:
            show_palette_cmd_def = _ui.commandDefinitions.addButtonDefinition('showPalette',
                                                                              'Customizable Content Center',
                                                                              'Show the customizable content center',
                                                                              './resources')

            # Connect to Command Created event.
            on_command_created = ShowPaletteCommandCreatedHandler()
            show_palette_cmd_def.commandCreated.add(on_command_created)
            handlers.append(on_command_created)

        # Add the command to the toolbar.
        panel = _ui.allToolbarPanels.itemById('InsertPanel')  # SolidScriptsAddinsPanel
        panel_control = panel.controls.itemById('showPalette')
        if not panel_control:
            button_control = panel.controls.addCommand(show_palette_cmd_def)
            # Make the button available in the panel.
            button_control.isPromotedByDefault = True
            button_control.isPromoted = True

        # panel_control = panel.controls.itemById('sendInfoToHTML')
        # if not panel_control:
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
        cmd_def = _ui.commandDefinitions.itemById('showPalette')
        if cmd_def:
            cmd_def.deleteMe()

        cmd = panel.controls.itemById('sendInfoToHTML')
        if cmd:
            cmd.deleteMe()
        cmd_def = _ui.commandDefinitions.itemById('sendInfoToHTML')
        if cmd_def:
            cmd_def.deleteMe()

        # _ui.messageBox('Stop addin')
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
