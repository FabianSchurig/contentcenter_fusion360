import adsk.core
import importlib
import inspect
import os
import sys
import traceback
import tempfile
import tarfile
import shutil

sys.path.append("./modules")
sys.path.append("./modules/modules")

import pip
import requests

version = "v1.2"
_app = None
_ui = None

def versiontuple(v):
    v = v.replace('v', '')
    return tuple(map(int, (v.split("."))))

def install(path, requirementsFileName):
    if hasattr(pip, 'main'):
        with open(requirementsFileName) as f:
            for line in f:
                pip.main(['install', '-U', line, '-t', path, '--ignore-installed', '-q'])
    else:
        with open(requirementsFileName) as f:
            for line in f:
                pip._internal.main(['install', '-U', line, '-t', path, '--ignore-installed', '-q'])


def update(context):
    global version, _ui
    currentFolder = os.path.dirname(os.path.realpath(__file__))
    currentFolder = os.path.join(currentFolder, '')
    # cwd = os.getcwd()

    releasesURI = 'https://api.github.com/repos/Bitfroest/contentcenter_fusion360/releases'

    r = requests.get(releasesURI)

    if r.status_code == 200:
        releases = r.json()
        tag_name = releases[0]['tag_name']
        tarball_url = releases[0]['tarball_url']
        published_at = releases[0]['published_at']
        # _ui.messageBox(str(tag_name))

        if versiontuple(tag_name) > versiontuple(version):
            # _ui.messageBox('Performing Update')
            # Create a local temporary folder
            with tempfile.TemporaryDirectory() as temp:
                tarball = requests.get(tarball_url)
                if tarball.status_code == 200:
                    tempFileName = os.path.join(temp, str(tag_name+'.tar.gz'))
                    tempFile = open(tempFileName, 'wb')
                    tempFile.write(tarball.content)
                    tempFile.close()

                    tar = tarfile.open(tempFileName, "r:gz")

                    folderName = os.path.join(tar.getmembers()[0].name.split('/')[0], '')
                    tar.extractall(path=temp)
                    tar.close()

                    tempDirectory = os.path.join(temp, folderName)

                    # delete all files in directory
                    for file in os.listdir(currentFolder):
                        filePath = os.path.join(currentFolder, file)
                        try:
                            if os.path.isfile(filePath):
                                os.unlink(filePath)
                            elif os.path.isdir(filePath): shutil.rmtree(filePath)
                        except Exception as e:
                            print(e)

                    # delete directory
                    os.rmdir(currentFolder)

                    # copy all extracted contents to add in folder
                    shutil.copytree(tempDirectory, os.path.join(currentFolder, ''))

                    if os.path.isfile(os.path.join(currentFolder, 'requirements.txt')):
                        modulesFolder= os.path.join(os.path.join(currentFolder, 'modules'), 'modules')
                        if not os.path.exists(modulesFolder):
                            os.makedirs(modulesFolder)
                        install(modulesFolder, os.path.join(currentFolder, 'requirements.txt'))

                    if os.path.isfile(os.path.join(os.path.join(currentFolder, 'modules'), 'ContentCenter.py')):
                        # updated and now reload the function
                        try:
                            reload(context)
                        except:
                            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                            pass
                        _ui.messageBox(str('Updated Add-In Custom Content Center'))

def run(context):
    global _app, _ui
    script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
    script_dir = os.path.dirname(script_path)
    module_dir = os.path.abspath(os.path.join(script_dir, "modules"))
    sys.path.append(module_dir)

    _app = adsk.core.Application.get()
    _ui = _app.userInterface

    try:
        import ContentCenter
        importlib.reload(ContentCenter)

        ContentCenter.run(context)
    except:
        _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
    finally:
        del sys.path[module_dir]

    try:
        update(context)
    except:
        _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
        pass

def stop(context):
    import ContentCenter
    ContentCenter.stop(context)

def reload(context):
    # You would call this from your github reload functionality, once the updated module is in place
    import ContentCenter
    ContentCenter.stop(context)
    importlib.reload(ContentCenter)
    ContentCenter.run(context)
