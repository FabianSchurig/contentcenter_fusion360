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

_script_path = os.path.abspath(inspect.getfile(inspect.currentframe()))
_script_dir = os.path.dirname(_script_path)
_module_dir = os.path.abspath(os.path.join(_script_dir, "modules"))
sys.path.append(_module_dir)
_module_module_dir = os.path.abspath(os.path.join(_module_dir, "modules"))
sys.path.append(_module_module_dir)

try:
    import requests
except:
    pass

_app = None
_ui = None

_is_mac_os = False

# checks if OS is MacOS
if platform.system() == 'Darwin':
    _is_mac_os = True


def _version_tuple(v):
    v = v.replace('v', '')
    return tuple(map(int, (v.split("."))))


def update(context):
    global _ui, _is_mac_os
    current_folder = os.path.dirname(os.path.realpath(__file__))
    current_folder = os.path.join(current_folder, '')
    # cwd = os.getcwd()
    try:
        with open(os.path.join(_script_dir, 'version.json')) as f:
            data = json.load(f)
            version = data['tag_name']
            print(version)
    except:
        version = "999"
        print('Failed:\n{}'.format(traceback.format_exc()))
        pass

    releases_uri = 'https://custom.hk-fs.de/uploads/version.json'

    if _is_mac_os:
        proc = subprocess.Popen(['curl', releases_uri], stdout=subprocess.PIPE)
        (out, err) = proc.communicate()
        j = json.loads(out.decode('utf-8'))
        tag_name = j['tag_name']
        tarball_url = j['tarball_url']
        published_at = j['published_at']

        if _version_tuple(tag_name) > _version_tuple(version):
            # Check if the URL is reachable
            out = subprocess.check_output(['curl', '-I', tarball_url])

            with tempfile.TemporaryDirectory() as temp:
                if out.decode().find('200') > 0:
                    # Download the tarball file in the temporary folder
                    temp_file_name = os.path.join(temp, str(tag_name + '.tar.gz'))
                    subprocess.call(['curl', '-o', temp_file_name, '-L', tarball_url])

                    tar = tarfile.open(temp_file_name, "r:gz")

                    folder_name = os.path.join(tar.getmembers()[0].name.split('/')[0], '')
                    tar.extractall(path=temp)
                    tar.close()

                    temp_directory = os.path.join(temp, folder_name)

                    # delete all files in directory
                    for file in os.listdir(current_folder):
                        file_path = os.path.join(current_folder, file)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as e:
                            print(e)

                    # delete directory
                    os.rmdir(current_folder)

                    # copy all extracted contents to add in folder
                    try:
                        shutil.copytree(temp_directory, os.path.join(current_folder, ''))
                    except:
                        _ui.messageBox('Content Center update failed, please install/repair again.')

                    if os.path.isfile(os.path.join(os.path.join(current_folder, 'modules'), 'ContentCenter.py')):
                        # updated and now reload the function
                        try:
                            reload(context)
                        except:
                            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                            pass
                        _ui.messageBox(str('Updated Add-In Custom Content Center'))

    else:
        r = requests.get(releases_uri)
        if r.status_code == 200:
            releases = r.json()
            tag_name = releases['tag_name']
            tarball_url = releases['tarball_url']
            published_at = releases['published_at']
            # _ui.messageBox(str(tag_name))

            if _version_tuple(tag_name) > _version_tuple(version):
                # _ui.messageBox('Performing Update')
                # Create a local temporary folder
                with tempfile.TemporaryDirectory() as temp:
                    tarball = requests.get(tarball_url)
                    if tarball.status_code == 200:
                        temp_file_name = os.path.join(temp, str(tag_name + '.tar.gz'))
                        tempFile = open(temp_file_name, 'wb')
                        tempFile.write(tarball.content)
                        tempFile.close()

                        tar = tarfile.open(temp_file_name, "r:gz")

                        folder_name = os.path.join(tar.getmembers()[0].name.split('/')[0], '')
                        tar.extractall(path=temp)
                        tar.close()

                        temp_directory = os.path.join(temp, folder_name)

                        # delete all files in directory
                        for file in os.listdir(current_folder):
                            file_path = os.path.join(current_folder, file)
                            try:
                                if os.path.isfile(file_path):
                                    os.unlink(file_path)
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                            except Exception as e:
                                print(e)

                        # delete directory
                        os.rmdir(current_folder)

                        # copy all extracted contents to add in folder
                        try:
                            shutil.copytree(temp_directory, os.path.join(current_folder, ''))
                        except:
                            _ui.messageBox('Content Center update failed, please install/repair again.')

                        if os.path.isfile(os.path.join(os.path.join(current_folder, 'modules'), 'ContentCenter.py')):
                            # updated and now reload the function
                            try:
                                reload(context)
                            except:
                                _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
                                pass
                            _ui.messageBox(str('Updated Add-In Custom Content Center'))


def run(context):
    global _app, _ui, _is_mac_os, _module_dir
    sys.path.append(_module_dir)

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
        del sys.path[_module_dir]


def stop(context):
    try:
        import ContentCenter
        ContentCenter.stop(context)
    except:
        pass


def reload(context):
    # You would call this from your github reload functionality, once the updated module is in place
    try:
        import ContentCenter
        ContentCenter.stop(context)
        importlib.reload(ContentCenter)
        ContentCenter.run(context)
    except:
        pass
