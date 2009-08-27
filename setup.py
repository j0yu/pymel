#!/usr/bin/env mayapy
import sys
import re
import os
import glob
import platform
from zipfile import ZipFile
from distutils.sysconfig import get_makefile_filename, get_python_lib
try:
    system = platform.system()
except:
    system = None
    
def test_dynload_modules():
    # start with a bit of a hack.  not sure the most reliable way to get the dynload directory
    # so we can import one of the most fundamental and use it's path
    import math
    dynload_dir = os.path.dirname( os.path.normpath( math.__file__ ) )
    print dynload_dir
    bad_modules = []
    print "testing Maya python installation for missing system libraries"
    for f in glob.glob( os.path.join(dynload_dir, '*.so') ):
        try:
            module_name = os.path.splitext( os.path.basename(f))[0]
            __import__( module_name , globals(), locals() )
        except ImportError, e:
            msg = str(e)
            if msg.startswith('lib'):
                msg += '. create a symbolic link pointing to an existing version of this lib' 
            print "Warning: Could not import module %s: %s" % ( module_name, msg)
            bad_modules.append( module_name )
    return bad_modules

def fix_makefile():
    # ensure python Makefile exists where expected    
    makefile = get_makefile_filename()
    if not os.path.exists(makefile):
        print "PyMEL setup: Makefile not found: %s. Attempting to correct" % makefile
        libdir = get_python_lib(plat_specific=1, standard_lib=1)
        zipinstall = os.path.join( os.path.dirname( get_maya_bin_dir() ),'lib', 'python%s%s.zip' % sys.version_info[0:2] )
        if os.path.exists(zipinstall):
            try:
                # extract the Makefile
                zip = ZipFile( zipinstall, 'r')
                # remove libdir
                zipmakefile = makefile.replace( libdir+os.sep, '')
                data = zip.read(zipmakefile)
                os.makedirs( os.path.dirname(makefile))
                f = open(makefile, 'w')
                f.write(data)
                f.close()
                print "PyMEL setup: successfully extracted Makefile from zip install into proper location"
                return
            except Exception, e:
                print "PyMEL setup: an error occurred while trying to fix the Makefile: %s" % e
        else:
            print "PyMEL setup: cannot fix. zip install was not found: %s" % zipinstall
        print ("distutils will most likely fail, complaining that this is an invalid python install. PyMEL setup\n" +
                "was unable to properly correct the problem. The root problem is that your python Makefile is missing")


def get_maya_version():

    # problem with service packs addition, must be able to match things such as :
    # '2008 Service Pack 1 x64', '2008x64', '2008', '8.5'

    try:
        versionStr = os.path.dirname( os.path.dirname( sys.executable ) )
        m = re.search( "((?:maya)?(?P<base>[\d.]{3,})(?:(?:[ ].*[ ])|(?:-))?(?P<ext>x[\d.]+)?)", versionStr)
        version = m.group('base')
        return version
    except:
        pass

def get_ply_version():
    if sys.version_info >= (2,6):
        return 'ply >2.0'
    return 'ply >2.0, <3.0'

def get_data_files():
    if get_maya_version() in ['2010'] and system == 'Darwin':
        return [('', ['extras/2010/osx/readline.so'])]
    return []

def get_mayapy_executable():   
    if os.name == 'posix':
        try:
            # matches on osx and linux due to /bin/../Frameworks/
            mayapy_bin = re.match('.*/bin/', sys.executable ).group(0) + 'mayapy'
            return mayapy_bin
        except:
            pass    
    return os.path.normpath( sys.executable )

def get_maya_bin_dir():
    return os.path.dirname( get_mayapy_executable() )


    
def main():
    if system == 'Linux':
        # do this first because ez_setup won't import if md5 can't be imported
        res = test_dynload_modules()  
        if '_hashlib' in res or '_md5' in res:
            raise RuntimeError, ("could not import %s compiled modules. this is usually due\n" % len(res) +
                                "to Maya's python being compiled on a different flavor or version\n" +
                                "of linux than you are running.\n" +
                                "to solve this quickly, for each missing library locate\n" +
                                "an existing version and make a symbolic link from the real lib to\n" +
                                "the missing lib")
        
    
        # makefile does not exist, so install will complain of "invalid python install"
        fix_makefile()  
    
    import ez_setup
    ez_setup.use_setuptools()
    from setuptools import setup
    import setuptools.command.easy_install
    
    # overwrite setuptools.command.easy_install.get_script_args
    # it's the only way to change the executable for ipymel
    if system == 'Darwin':
        orig_script_args = setuptools.command.easy_install.get_script_args
        orig_nt_quote_arg = setuptools.command.easy_install.nt_quote_arg
        # on osx we need to use '/usr/bin/env /Applications....mayapy', but setuptools tries to wrap this in quotes
        # because it has a space in it. disable this behavior
        def nt_quote_arg(arg):
            return arg
    
        if 'install' in sys.argv:
            # set default script installation directory
            # on osx the python binary is deep within the frameworks directory,
            # so the binaries get installed there.  instead, put them in the maya bin directory
            args = list(sys.argv)
            is_set = False
            # looking for a line like:  '--install-scripts=/Applications/Autodesk/maya2010/Maya.app/Contents/bin'
            for arg in args[1:]:
                if arg.split('=')[0] in [ '--install-scripts', '--install-dir' ]:
                    is_set = True
                    break
            if not is_set:
                args.append( '--install-scripts=' + get_maya_bin_dir() )
                sys.argv = args
             
        
        def get_script_args(dist, executable=None, wininst=False):
            executable = get_mayapy_executable()  
            executable = '/usr/bin/env ' + executable
            return orig_script_args(dist, executable, wininst)
    
        setuptools.command.easy_install.nt_quote_arg = nt_quote_arg
        setuptools.command.easy_install.get_script_args = get_script_args
    
    try:
        setup(name='pymel',
              version='0.9.2',
              description='Python in Maya Done Right',
              long_description = """
        PyMEL makes python scripting with Maya work the way it should. Maya's command module is a direct translation
        of mel commands into python commands. The result is a very awkward and unpythonic syntax which does not take 
        advantage of python's strengths -- particulary, a flexible, object-oriented design. PyMEL builds on the cmds 
        module by organizing many of its commands into a class hierarchy, and by customizing them to operate in a more 
        succinct and intuitive way. """,
              author='Chad Dombrova',
              author_email='chadrik@gmail.com',
              url='http://code.google.com/p/pymel/',
              packages=['pymel','pymel.api', 'pymel.core', 'pymel.mayahook', 'pymel.tools', 'pymel.tools.mel2py', 'pymel.util' ],
              entry_points = {'console_scripts' : 'ipymel = pymel.tools.ipymel:main' },
              package_data={'pymel': ['*.bin', '*.conf' ] },
              install_requires=['BeautifulSoup >3.0', get_ply_version(), 'ipython'],
              tests_require=['nose'],
              test_suite = 'nose.collector',
              data_files = get_data_files()
             )
    finally:
        if system == 'Darwin':
            # restore
            setuptools.command.easy_install.get_script_args = orig_script_args
            setuptools.command.easy_install.nt_quote_arg = orig_nt_quote_arg

if __name__ == '__main__':
    main()

    
