import adsk.core
import importlib
import inspect
import os
import sys
import traceback
import tempfile
import tarfile
import shutil
import platform
import subprocess
import json

script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
script_dir = os.path.dirname(script_path)
module_dir = os.path.abspath(os.path.join(script_dir, "modules"))
sys.path.append(module_dir)
module_module_dir = os.path.abspath(os.path.join(module_dir, "modules"))
sys.path.append(module_module_dir)

try:
    import requests
except:
    pass

_app = None
_ui = None

isMac = False

# checks if OS is MacOS
if platform.system() == 'Darwin':
    isMac = True

def versiontuple(v):
    v = v.replace('v', '')
    return tuple(map(int, (v.split("."))))

def update(context):
    global _ui, isMac
    currentFolder = os.path.dirname(os.path.realpath(__file__))
    currentFolder = os.path.join(currentFolder, '')
    # cwd = os.getcwd()
    try:
        with open(os.path.join(script_dir,'version.json')) as f:
            data = json.load(f)
            version = data['tag_name']
            print(version)
    except:
        version = "999"
        print('Failed:\n{}'.format(traceback.format_exc()))
        pass

    releasesURI = 'https://custom.hk-fs.de/uploads/version.json'

    if isMac:
        proc = subprocess.Popen(['curl', releasesURI], stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        j = json.loads(out.decode('utf-8'))
        tag_name = j['tag_name']
        tarball_url = j['tarball_url']
        published_at = j['published_at']

        if versiontuple(tag_name) > versiontuple(version):
            # Check if the URL is reachable
            out = subprocess.check_output(['curl', '-I', releasesURI])

            with tempfile.TemporaryDirectory() as temp:
                if out.decode().find('Status: 200 OK') > 0:
                    # Download the tarball file in the temporary folder
                    tempFileName = os.path.join(temp, str(tag_name+'.tar.gz'))
                    subprocess.call(['curl', '-o', tempFileName, '-L', tarball_url])

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

                    if os.path.isfile(os.path.join(os.path.join(currentFolder, 'modules'), 'ContentCenter.py')):
                        # updated and now reload the function
                        try:
                            reload(context)
                        except:
                            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                            pass
                        _ui.messageBox(str('Updated Add-In Custom Content Center'))

    else:
        r = requests.get(releasesURI)
        if r.status_code == 200:
            releases = r.json()
            tag_name = releases['tag_name']
            tarball_url = releases['tarball_url']
            published_at = releases['published_at']
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

                        if os.path.isfile(os.path.join(os.path.join(currentFolder, 'modules'), 'ContentCenter.py')):
                            # updated and now reload the function
                            try:
                                reload(context)
                            except:
                                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                                pass
                            _ui.messageBox(str('Updated Add-In Custom Content Center'))

def run(context):
    global _app, _ui, isMac, module_dir
    sys.path.append(module_dir)

    _app = adsk.core.Application.get()
    _ui = _app.userInterface

    try:
        import ContentCenter
        importlib.reload(ContentCenter)

        ContentCenter.run(context)
        update(context)
    except:
        _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
    finally:
        del sys.path[module_dir]

def stop(context):
    import ContentCenter
    ContentCenter.stop(context)

def reload(context):
    # You would call this from your github reload functionality, once the updated module is in place
    import ContentCenter
    ContentCenter.stop(context)
    importlib.reload(ContentCenter)
    ContentCenter.run(context)
