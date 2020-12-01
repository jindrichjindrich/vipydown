import os
import sys
import glob
import logging
import subprocess
import datetime
import shutil
from urllib import request

SCRIPT_FULLNAME =  os.path.abspath(__file__)
ROOT_DIR, SCRIPT_NAME = os.path.split(SCRIPT_FULLNAME)
SCRIPT_BASE = os.path.splitext(SCRIPT_NAME)[0] # bare script name without an extension
SCRIPT_LNK =  SCRIPT_BASE + '.lnk'
VERSION = '1.0.1'
f"""
Python standalone script/module to launch local server/web browser gui
for downloading youtube videos using third party youtube_dl module

Run "python {SCRIPT_NAME} ?" for help.
"""

"""
v1.0.1 2020-12-01
- fixed bug reading logs when already downloaded file is beeing reported
v1.0.0 2020-11-29
- showing already downloaded files by parsing log files
- allowing to use download_dir subfolder (to group similar files)

"""

log = logging.getLogger(__name__)
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
    download_subdir = form.getvalue('download_subdir', '')
    submit = form.getvalue('submit', '')
    urls = urls_list[0] if urls_list else ''
    urls = '\n'.join([u.strip() for u in urls.split() if u.strip()])
    kwargs = get_kwargs(download_subdir=download_subdir)

    if urls:
        run_download(urls = urls.split(), download_subdir=download_subdir, skip_install=True)
        message = 'Started download of:\n{}'.format(urls)
    else:
        if submit:
            message = 'No urls specified'
        else:
            message = ''

    download_info = get_download_info(kwargs['log_dir'], kwargs['download_dir'])

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
    <div>Optional download subfolder: <input name="download_subdir" value="{download_subdir}" /></div>
    <div><textarea name="urls" rows="10" cols="80">{urls}</textarea></div>
    <div><input type="submit" name="submit" value="Download" /></div>
  </form>
</div>
<div id="message">{message}</div>
<div id="download_info">{download_info}<div>
</body>
</html>
""")

def get_kwargs(**fkwargs):
    """Get parameters common to all run_ methods

    Gather the parameters values in the order (the later will remain):
    - defaults
    - ini file
    - command line paramaters
    - explicit fkwargs
    """
    import sys
    ini_file = os.path.join(ROOT_DIR, SCRIPT_BASE + '.ini')
    kwargs = {}
    # update first from inifile
    if os.path.exists(ini_file):
        with open(ini_file, 'br') as f:
            text = f.read().decode('utf-8-sig')
            ikwargs = dict([l.strip().split('=', 1) for l in text.split('\n') if l.count('=')])
        kwargs.update(ikwargs)
    ckwargs = dict([p.split('=', 1) for p in sys.argv[2:] if p.count('=')])
    # update second from command line params
    kwargs.update(ckwargs)
    # update last from the explicit get_kwargs params
    kwargs.update(fkwargs)

    DEF = {'port': 8000, 'host': '', 'data_dir': os.getcwd(),
        'download_dir': os.path.join('{USERPROFILE}'.format(**os.environ), 'Downloads'),
        'download_subdir': '',
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
    if kwargs['download_subdir']:
        kwargs['download_fulldir'] = os.path.join(kwargs['download_dir'], kwargs['download_subdir'])
        if not os.path.exists(kwargs['download_fulldir']):
            os.makedirs(kwargs['download_fulldir'])
    else:
        kwargs['download_fulldir'] = kwargs['download_dir']
    return kwargs

def get_now_suffix():
    return datetime.datetime.now().isoformat()[:19].replace(':','-')

def get_datetime_from_suffix(suffix):
    """From the suffix = 'YYYY-MM-DDTHH-MM-SS' string get the Python datetime value"""
    try:
        dt = datetime.datetime.strptime(suffix, '%Y-%m-%dT%H-%M-%S')
    except:
        log.exception('get_datetime_from_suffix({})'.format(suffix))
        dt = None
    return dt

def get_downloads_info_from_log_file(log_file, download_dir):
    """
log_file name: vipydown_download_SUBDIR_2020-11-28T18-54-07.log
(old: vipydown_download_2020-11-28T18-54-07.log)

[download] Destination: NEW- 5 minute arm workout-t2EypNxeABs.mp4
...
[download]  59.8% of 66.80MiB at  1.91MiB/s ETA 00:14
...
[download] 100% of 66.80MiB in 00:27

[ffmpeg] Merging formats into "Cyklistika-P2hfIpaoH4g.webm"
Deleting original file Cyklistika-P2hfIpaoH4g.f244.webm (pass -k to keep)
Deleting original file Cyklistika-P2hfIpaoH4g.f251.webm (pass -k to keep)

    """
    downloads_info = {}
    parts = os.path.splitext(os.path.split(log_file)[1])[0].split('_')
    dest_str = '[download] Destination: '
    end_str = '[download] 100% of '
    merge_str = '[ffmpeg] Merging formats into '
    st = os.stat(log_file)
    download_info = {}

    def add_download_info():
        bfn = download_info.get('filename', '')
        if not bfn:
            return
        parts = bfn.split('.')
        if len(parts) >= 3:
            k = '.'.join(bfn.split('.')[:-2])
        else:
            k = parts[0]
        downloads_info[k] = download_info

    with open(log_file) as f:
        for line in f.readlines():
            if not line.strip():
                continue

            if line.startswith(dest_str):
                if download_info:
                    add_download_info()

                download_info = {
                    'log_file': log_file, 'download_dir': download_dir,
                    'download_subdir': '', 'download_started': None, 'status': 'unknown',
                    'filename': '', 'filesize': '', 'download_completed': None,
                }
                if len(parts) == 3:
                    #old log filename format
                    download_info['download_subdir'] = ''
                    download_info['download_started'] = get_datetime_from_suffix(parts[2])
                elif len(parts) >= 4:
                    #new log filename format
                    download_info['download_subdir'] = parts[2]
                    download_info['download_started'] = get_datetime_from_suffix(parts[3])

                download_info['filename'] = line.strip()[len(dest_str):]
                download_info['status'] = 'download_started'

            if line.startswith(end_str):
                download_info['status'] = 'download_completed'
                download_info['download_completed'] = datetime.datetime.fromtimestamp(st.st_atime)
                eparts = line.strip().split(' ')
                if len(eparts) >= 4:
                    download_info['filesize'] = eparts[3]
                add_download_info()
                download_info = {}

            if line.startswith(merge_str):
                fn = line[len(merge_str):].strip().strip('"')
                k = os.path.splitext(fn)[0]
                if k in downloads_info:
                    downloads_info[k]['filename'] = fn

    return downloads_info.values()

def get_download_info(log_dir, download_dir):
    """Return html text info about downloaded or beeing downloaded files
    Using log files in the log_dir
    """
    lines = []
    for log_file in sorted(glob.glob(os.path.join(log_dir, f'{SCRIPT_BASE}_download_*.log')), reverse=True, key=lambda i: i.split('_')[-1]):
        #fn = os.path.join(log_dir, basefn)
        log.info(log_file)
        for download_info in get_downloads_info_from_log_file(log_file, download_dir):
            if not download_info['filename']:
                continue
            rec = {}
            s = download_info['download_subdir']
            if s:
                s = s + os.sep
            rec['File'] = s + download_info['filename']
            if download_info['download_completed']:
                rec['Downloaded'] = str(download_info['download_completed'])[:19]
            else:
                rec['Download started'] = str(download_info['download_started'])[:19]
            if download_info['filesize']:
                rec['Size'] = download_info['filesize']
            line = ' '.join(['<b>{}:</b> {}'.format(*kv) for kv in rec.items()])
            lines.append(line)
    return '<br />'.join(lines)

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

def is_server_running(**kwargs):
    url = get_client_url(**kwargs)
    try:
        f = request.urlopen(url, timeout=5)
        if f.status == 200:
            return True
    except:
        pass
    return False

def run_server():
    import http.server as server
    server_class = server.HTTPServer
    class Handler(server.CGIHTTPRequestHandler):
        cgi_directories = ['/', '.']

    kwargs = get_kwargs()
    if is_server_running(**kwargs):
        log.info(f'{SCRIPT_BASE} server is already running.')
        run_client()
        return
    install(upgrade='1')

    suffix = get_now_suffix()
    log.addHandler(logging.FileHandler(
        os.path.join(kwargs['log_dir'], f'{SCRIPT_BASE}_server_{suffix}.log')
    ))
    now = datetime.datetime.now()
    log.info(f'{SCRIPT_BASE} server starting {now}')

    handler_class = Handler
    server_address = (kwargs['host'], kwargs['port'])
    httpd = server_class(server_address, handler_class)
    run_client()
    httpd.serve_forever()

    now = datetime.datetime.now()
    log.info(f'{SCRIPT_BASE} server stopped {now}')

def get_client_url(**kwargs):
    """Return url at which the server is accessible in web browser"""
    if not kwargs['host']:
        kwargs['host'] = 'localhost'
    url = f'http://{kwargs["host"]}:{kwargs["port"]}/{SCRIPT_NAME}'
    return url

def run_client():
    import webbrowser
    kwargs = get_kwargs()
    url = get_client_url(**kwargs)
    log.info(f'Opening web browser at {url}')
    webbrowser.open(url)

def run_download(urls=[], download_subdir='', skip_install=False):
    #see server.CGIHTTPRequestHandler run_cgi
    if not skip_install:
        install()
    cmd = os.path.join(sys.prefix, 'python.exe')
    result = {}
    env = {}
    kwargs = get_kwargs(download_subdir=download_subdir)

    cur_dir = os.getcwd()
    os.chdir(kwargs['download_fulldir'])
    try:
        cmdline = [cmd, '-m', 'youtube_dl']
        if urls:
            if isinstance(urls, str):
                urls = [u.strip() for u in urls.split()]
            cmdline.extend(urls)
        suffix = get_now_suffix()
        log_fn = os.path.join(kwargs['log_dir'], f'{SCRIPT_BASE}_download_{download_subdir}_{suffix}.log')
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

def _get_lnk_dic():
    base_lnk = SCRIPT_LNK
    startup_dir = os.path.join("{APPDATA}".format(**os.environ), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    desktop_dir = os.path.join("{USERPROFILE}".format(**os.environ), 'Desktop')
    desktop_lnk_file = os.path.join(desktop_dir, base_lnk)
    startup_lnk_file = os.path.join(startup_dir, base_lnk)
    lnk_file = get_lnk_filename() #os.path.join(ROOT_DIR, base_lnk)
    python_exe = os.path.join(sys.prefix, 'python.exe')
    vbs_file = os.path.join(ROOT_DIR, f'{SCRIPT_BASE}_lnk.vbs')
    return locals().copy()

def run_rm_lnk():
    f"""Remove all lnk files.
    I.e., {SCRIPT_NAME} will think it was not installed yet. Also, remove
    all the executable trash the {SCRIPT_NAME} makes if it will be removed.
    """
    dic = _get_lnk_dic()
    for k in ['vbs_file', 'startup_lnk_file', 'desktop_lnk_file', 'lnk_file']:
        if os.path.exists(dic[k]):
            os.unlink(dic[k])
            log.info('Removed file {}'.format(dic[k]))

def run_make_lnk():
    rf"""Create Windows shortcut file for starting a {SCRIPT_BASE} server.

    Create the {SCRIPT_LNK} only if it does not exist yet. Then copy it to startup folder
    (if not present there yet) and to the desktop (if it is not there yet)

    Startup folder:
    C:\Users\current_user\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\

    Desktop folder:
    C:\Users\current_user\Desktop

    See:
    https://superuser.com/questions/392061/how-to-make-a-shortcut-from-cmd
    """
    dic = _get_lnk_dic()

    VBS = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{dic['lnk_file']}"
Set oLink = oWS.CreateShortcut(sLinkFile)
    oLink.TargetPath = "{dic['python_exe']}"
    oLink.Arguments = "{SCRIPT_FULLNAME} server"
 '  oLink.Description = "{SCRIPT_BASE} server"
 '  oLink.HotKey = "ALT+CTRL+V"
 '  oLink.IconLocation = "C:\Program Files\MyApp\MyProgram.EXE, 2"
 '  oLink.WindowStyle = "1"
    oLink.WorkingDirectory = "{ROOT_DIR}"
oLink.Save
    """
    if not os.path.exists(dic['vbs_file']):
        with open(dic['vbs_file'], 'w') as f:
            f.write(VBS)
        log.info('File {} created.'.format(dic['vbs_file']))
    if not os.path.exists(dic['lnk_file']):
        res = subprocess.run(['cscript', dic['vbs_file']], check=True, shell=True)
        log.info('Creating {}, {} called returncode={}'.format(dic['lnk_file'], dic['vbs_file'], res.returncode))
    for k in ['startup_lnk_file', 'desktop_lnk_file']:
        if not os.path.exists(dic[k]):
            shutil.copy(dic['lnk_file'], dic[k])
            log.info('Copied {} to {}'.format(dic['lnk_file'], dic[k]))

def get_lnk_filename():
    return os.path.join(ROOT_DIR, SCRIPT_LNK)

def is_set_up():
    return os.path.exists(get_lnk_filename())

def run_setup():
    install(upgrade='1')
    run_make_lnk()

def add_handler():
    log.addHandler(logging.StreamHandler())
    log.setLevel(logging.INFO)

if __name__ == '__main__':
    arg = sys.argv[1] if sys.argv[1:] else ''
    if arg.lstrip('-') in ['help', 'h', '?']:
        kwargs = get_kwargs()
        print(f'Usage: python {SCRIPT_NAME} ACTION [param1=value1] ... (python >= 3.6 in PATH required)')
        print(f'Version: {VERSION}')
        print(f'ACTIONs:')
        print(f'  help - (or "[-]h", "[-]?") show this help text')
        print( '  server [port={port}] [host={host}] [data_dir={data_dir}]'.format(**kwargs))
        print( '      [log_dir={log_dir}] [download_dir={download_dir}] '.format(**kwargs))
        print( '      - run as cgi web server (also calls "client" first)')
        print(f'        the above parameters can be specified in {ROOT_DIR}\{SCRIPT_BASE}.ini file')
        print( '  client [port={port}] [host={host}] ...  '.format(**kwargs))
        print( '      - open web page pointing to the server')
        print(f'  download URL1 [URL2 ...]')
        print( '      - download the given youtube videos')
        print(f'  install [upgrade=1] ')
        print(f'      - install youtube_dl module')
        print(f'        called also by "server" (upgrade=1) and "download"')
        print(f'  make_lnk ')
        print(f'      - create {SCRIPT_LNK} file and copy it')
        print(f'        to user''s Windows startup folder and Desktop folder')
        print(f'  setup ')
        print(f'      - call install and make_lnk, ')
        print(f'        after PC restart it should work')
        print(f'  rm_lnk - remove all .lnk files made by make_lnk')
        print(f'  ... (other or no ACTION)')
        print(f'      - run as cgi script,')
        print(f'        if {SCRIPT_LNK} not found, "setup" is called instead')
    elif arg in ['server', 'run_server']:
        add_handler()
        run_server()
    elif arg in ['client', 'run_client']:
        add_handler()
        run_client()
    elif arg in ['download', 'run_download']:
        add_handler()
        run_download(urls=sys.argv[2:])
    elif arg in ['install', 'run_install']:
        add_handler()
        run_install()
    elif arg in ['make_lnk', 'run_make_lnk']:
        add_handler()
        run_make_lnk()
    elif arg in ['rm_lnk', 'run_rm_lnk']:
        add_handler()
        run_rm_lnk()
    elif arg in ['setup', 'run_setup']:
        add_handler()
        run_setup()
    else:
        if not is_set_up():
            add_handler()
            run_setup()
        else:
            run_cgi()
