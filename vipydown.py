"""
https://docs.python.org/3.8/library/cgi.html

"""
import os
import sys
import logging
import subprocess
import datetime
import shutil

log = logging.getLogger(__name__)
SCRIPT_FULLNAME =  os.path.abspath(__file__)
ROOT_DIR, SCRIPT_NAME = os.path.split(SCRIPT_FULLNAME)
SCRIPT_BASE = os.path.splitext(SCRIPT_NAME)[0] # bare script name without an extension
SCRIPT_LNK =  SCRIPT_BASE + '.lnk'

try:
    import wingdbstub
except ImportError:
    pass

def run_cgi():
    import cgi

    import cgitb
    cgitb.enable()

    form = cgi.FieldStorage()
    urls_list = form.getlist('urls')
    urls = urls_list[0] if urls_list else ''
    urls = '\n'.join([u.strip() for u in urls.split() if u.strip()])
    kwargs = get_kwargs()
    if urls:
        run_download(urls = urls.split(), skip_install=True)
    print('Content-Type: text/html')
    print()
    print(f"""
<html>
<!-- Run in cmd window "python {SCRIPT_NAME} help" to get help on {SCRIPT_NAME} -->
<head>
    <title>Video (using Python) Download </title>
</head>
<body>
<h1>List of addresses of Youtube videos to download </h1>
<p>Enter the URLs (web addreses), one per line, of the Youtube videos to be downloaded to {kwargs['download_dir']} folder</p>
<div>
  <form>
    <div><textarea name="urls" rows="10" cols="80">{urls}</textarea></div>
    <div><input type="submit" value="Download" /></div>
  </form>
</div>
</body>
</html>
""")

def get_kwargs():
    import sys
    ini_file = os.path.join(ROOT_DIR, SCRIPT_BASE + '.ini')
    kwargs = {}
    if os.path.exists(ini_file):
        with open(ini_file) as f:
            ikwargs = dict([l.strip().split('=', 1) for l in f.readlines() if l.count('=')])
        kwargs.update(ikwargs)
    ckwargs = dict([p.split('=', 1) for p in sys.argv[2:] if p.count('=')])
    kwargs.update(ckwargs)

    DEF = {'port': 8000, 'host': '', 'data_dir': os.getcwd(),
        'download_dir': os.path.join('{USERPROFILE}'.format(**os.environ), 'Downloads'),
        'log_dir': '', # 'log_dir' will be added
    }
    for k in DEF:
        if not k in kwargs:
            kwargs[k] = DEF[k]
        if type(DEF[k]) == int:
            kwargs[k] = int(kwargs[k])

    if not os.path.exists(kwargs['data_dir']):
        os.makedirs(kwargs['data_dir'])
    if not kwargs.get('log_dir'):
        kwargs['log_dir'] = os.path.join(kwargs['data_dir'], 'log')
    if not os.path.exists(kwargs['log_dir']):
        os.makedirs(kwargs['log_dir'])
    if not os.path.exists(kwargs['download_dir']):
        os.makedirs(kwargs['download_dir'])
    return kwargs

def get_now_suffix():
    return datetime.datetime.now().isoformat()[:19].replace(':','-')

def install(upgrade=''):
    """https://stackoverflow.com/questions/12332975/installing-python-module-within-code
    """
    mname = 'youtube_dl'
    res = b''
    exe = os.path.join(sys.prefix, 'python.exe')
    if upgrade:
        res = subprocess.check_output([exe, "-m", "pip", "install", "-U", mname])
        import youtube_dl
    else:
        try:
            import youtube_dl
        except ImportError:
            res = subprocess.check_output([exe, "-m", "pip", "install", mname])
        finally:
            import youtube_dl
    return res.decode()

def run_install():
    kwargs = get_kwargs()
    res = install(upgrade=kwargs.get('upgrade'))
    print(res)

def run_server():
    install(upgrade='1')
    import http.server as server
    server_class = server.HTTPServer
    class Handler(server.CGIHTTPRequestHandler):
        cgi_directories = ['/', '.']
    kwargs = get_kwargs()
    suffix = get_now_suffix()
    log.addHandler(logging.FileHandler(
        os.path.join(kwargs['log_dir'], f'{SCRIPT_BASE}_server_{suffix}.log')
    ))

    handler_class = Handler
    server_address = (kwargs['host'], kwargs['port'])
    httpd = server_class(server_address, handler_class)
    run_client()
    httpd.serve_forever()

def run_client():
    import webbrowser
    kwargs = get_kwargs()
    if not kwargs['host']:
        kwargs['host'] = 'localhost'
    url = f'http://{kwargs["host"]}:{kwargs["port"]}/{SCRIPT_NAME}'
    webbrowser.open(url)

def run_download(urls=[], skip_install=False):
    #see server.CGIHTTPRequestHandler run_cgi
    if not skip_install:
        install()
    cmd = os.path.join(sys.prefix, 'python.exe')
    result = {}
    env = {}
    kwargs = get_kwargs()

    cur_dir = os.getcwd()
    os.chdir(kwargs['download_dir'])
    try:
        cmdline = [cmd, '-m', 'youtube_dl']
        if urls:
            if isinstance(urls, str):
                urls = [u.strip() for u in urls.split()]
            cmdline.extend(urls)
        suffix = get_now_suffix()
        log_fn = os.path.join(kwargs['log_dir'], f'{SCRIPT_BASE}_download_{suffix}.log')
        f = open(log_fn, 'a')
        try:
            proc = subprocess.Popen(cmdline, stdout=f, stderr=f)
            poll = proc.poll()
            if poll is None:
                result['process'] = proc
            else:
                log.error('Popen({}) failed with exit code {}.'.format(cmdline, poll))
                result['error'] = 'PopenError({})'.format(poll)
            #proc.pid = 15459
            #proc.args = ['c:\\Users\\jindrich\\Anaconda2\\envs\\printwes\\pythonw', 'd:\\projects\\ZebraFishDB-dev\\printwes\\printwes_server.py', 'secure=', 'use_tokens=', 'instances_dir=C:\\Users\\jindrich\\AppData\\Roaming\\PRINTW~1']
            #use: proc.terminate() or proc.kill() to terminate the process
            #     proc.poll() ... return None if the process is running, otherwise exit code (0 for OK, > 0 some error)
        except OSError:
            #print("Windows Error occured")
            log.exception('run_download cmdline={}'.format(cmdline))
            result['error'] = 'OSError'
        finally:
            #f.close() ... do not close for background process ...
            pass

        #stdout, stderr = proc.communicate(data)
        #proc.stderr.close()
        #proc.stdout.close()
        #status = proc.returncode

        #if status:
        #    self.log_error("CGI script exit status %#x", status)
        #else:
        #    self.log_message("CGI script exited OK")
    finally:
        os.chdir(cur_dir)
    return result #{'stdout': stdout, 'stderr': stderr, 'status': status}

def get_lnk_filename():
    return os.path.join(ROOT_DIR, BASE_LNK)

def run_make_lnk():
    r"""Create Windows shortcut file for starting a vipydown server.

    Create the vipydown.lnk only if it does not exist yet. Then copy it to startup folder
    (if not present there yet)

    Startup folder:
    C:\Users\current_user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\
    See:
    https://superuser.com/questions/392061/how-to-make-a-shortcut-from-cmd
    """
    base_lnk = SCRIPT_LNK
    startup_dir = os.path.join("{APPDATA}".format(**os.environ), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    startup_link_file = os.path.join(startup_dir, base_lnk)
    link_file = get_lnk_filename() #os.path.join(ROOT_DIR, base_lnk)
    python_exe = os.path.join(sys.prefix, 'python.exe')

    VBS = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{link_file}"
Set oLink = oWS.CreateShortcut(sLinkFile)
    oLink.TargetPath = "{python_exe}"
    oLink.Arguments = "{SCRIPT_FULLNAME} server"
 '  oLink.Description = "{SCRIPT_BASE} server"
 '  oLink.HotKey = "ALT+CTRL+V"
 '  oLink.IconLocation = "C:\Program Files\MyApp\MyProgram.EXE, 2"
 '  oLink.WindowStyle = "1"
    oLink.WorkingDirectory = "{ROOT_DIR}"
oLink.Save
    """
    vbs_fn = os.path.join(ROOT_DIR, f'{SCRIPT_BASE}_lnk.vbs')
    if not os.path.exists(vbs_fn):
        with open(vbs_fn, 'w') as f:
            f.write(VBS)
    if not os.path.exists(link_file):
        res = subprocess.run(['cscript', vbs_fn], check=True, shell=True)
        log.info('{} called returncode={}'.format(vbc_fn, res.returncode))
    if not os.path.exists(startup_link_file):
        shutil.copy(link_file, startup_link_file)

def get_lnk_filename():
    return os.path.join(ROOT_DIR, SCRIPT_LNK)

def is_set_up():
    return os.path.exists(get_lnk_filename())

def run_setup():
    install(upgrade='1')
    run_make_lnk()

if __name__ == '__main__':
    arg = sys.argv[1] if sys.argv[1:] else ''
    if arg.lstrip('-') in ['help', 'h', '?']:
        print(f'Usage: {SCRIPT_NAME} ACTION param1=value1 ...(python >= 3.6 required)')
        print(f'       {SCRIPT_NAME} help - show this help text')
        print(f'       {SCRIPT_NAME} server port=8000 host=  - run as cgi server')
        print(f'       {SCRIPT_NAME} client port=8000 host=  - open web page pointing to the server')
        print(f'       {SCRIPT_NAME} download URL1 [URL2 ...] - download the given youtube videos')
        print(f'       {SCRIPT_NAME} install [upgrade=1] - install youtube_dl module')
        print(f'                   called also by "server" (u=1) and "download"')
        print(f'       {SCRIPT_NAME} make_lnk - create vipydown.lnk file and copy it')
        print(f'                   to Windows startup folder (to autostart server)')
        print(f'       {SCRIPT_NAME} setup - call install and make_lnk, ')
        print(f'                           after PC restart it should work')
        print(f'       {SCRIPT_NAME} ... (other or no ACTION) - run as cgi script')
        print(f'                   if vipydown.lnk not found, "setup" is called first')
    elif arg == 'server':
        run_server()
    elif arg == 'client':
        run_client()
    elif arg == 'download':
        run_download(urls=sys.argv[2:])
    elif arg == 'install':
        run_install()
    elif arg == 'make_lnk':
        run_make_lnk()
    else:
        if not is_set_up():
            run_setup()
        else:
            run_cgi()