#!/usr/bin/env mayapy

#nosetests --with-doctest -v pymel --exclude '(windows)|(tools)|(arrays)|(example1)'

#import doctest
import sys, platform, os, os.path, shutil, subprocess, time, inspect

try:
    import nose
except ImportError, e:
    print "To run pymel's tests you must have nose installed: http://code.google.com/p/python-nose"
    raise e

if os.name == 'nt':
    app_dir = os.environ['USERPROFILE']
    
    # Vista or newer... version() returns "6.x.x"
    if int(platform.version().split('.')[0]) > 5:
        app_dir = os.path.join( app_dir, 'Documents')
    else:
        app_dir = os.path.join( app_dir, 'My Documents')
else:
    app_dir = os.environ['HOME']
    
if platform.system() == 'Darwin':
    app_dir = os.path.join( app_dir, 'Library/Preferences/Autodesk/maya' )    
else:
    app_dir = os.path.join( app_dir, 'maya' )

backup_dir = app_dir + '.bak'

DELETE_BACKUP_ARG = '--delete-maya-user-backup'

class RemoveBackupError(Exception): pass

def nose_test(module=None, extraArgs=None):
    """
    Run pymel unittests / doctests
    """

    noseKwArgs={}
    noseArgv = "dummyArg0 --with-doctest -v --noexe ".split()
    if module is None:
        module = 'pymel'
        exclusion = 'windows tools example1 .*testingutils pmcmds testPa'
        noseArgv += ['--exclude', '|'.join( [ '(%s)' % x for x in exclusion.split() ] )  ]
           
    if inspect.ismodule(module):
        noseKwArgs['module']=module
    else:
        noseArgv.append(module)
    if extraArgs is not None:
        noseArgv.extend(extraArgs)
    noseKwArgs['argv'] = noseArgv
    nose.main( **noseKwArgs)


def backupAndTest(extraNoseArgs):
    if os.path.isdir(backup_dir):
        print "backup dir %r already exists - aborting" % backup_dir
    else:
        print "backing up Maya user directory", app_dir
        shutil.move( app_dir, backup_dir )
        
        try:
            nose_test( extraArgs=extraNoseArgs )
        except Exception, e:
            print e
        finally:
            try:
                removeBackup()
            except RemoveBackupError:
                # on windows, maya never seems to exit cleanly unless the
                # process is completely exited - it keeps open access to
                # 'mayaLog', with the result that you can't delete the
                # backup_dir.  only way I know of around this is to delete
                # backup_dir in a completely separate process...
                print "initial Maya user directory restore failed - trying from separate process"                
                
                os.spawnl(os.P_NOWAIT,
                          sys.executable, os.path.basename(sys.executable),
                          __file__, DELETE_BACKUP_ARG)

def removeBackup(retryTime=.1, printFailure=False):
    print "restoring Maya user directory", app_dir

    lastException = None
    start = time.time()
    while os.path.isdir( app_dir ):
        # Check elapsed time AFTER trying to delete dir -
        # otherwise, if some other thread gets priority while we are
        # sleeping, and it's a while before the thread wakes up, we might
        # check once when almost no time has passed, sleep, wake up after
        # a lot of time has passed, and not check again...
        try:
            shutil.rmtree( app_dir )
        except Exception, e:
            lastException = e
            # print("print - unable to delete '%s' - elapsed time: %f" %
            #        (app_dir, time.time() - start))
            time.sleep(.2)
        else:
            lastException = None
            
        if time.time() - start > retryTime:
            break

    if lastException is not None:
        if printFailure:
            print('Error deleting "%s" - manually delete and rename/move "%s"' %
                   (app_dir, backup_dir))
        raise RemoveBackupError
    else:  
        shutil.move( backup_dir, app_dir )
        print "done"

if __name__ == '__main__':
    if DELETE_BACKUP_ARG not in sys.argv:
        backupAndTest(sys.argv[1:])
    else:
        # Maya may take some time to shut down / finish writing to files - 
        # give it 2 seconds
        removeBackup(retryTime=2, printFailure=True)