#!/usr/bin/env python3
""" Compile the application and create a release. """

import sys
import os
import shutil
import subprocess
import tempfile
import time
import datetime
import json
import re
import getopt

from PyInstaller.__main__ import run as run_pyinstaller

BASE_DIR = os.path.split( os.path.abspath(__file__) )[ 0 ]

MAIN_SCRIPT = "vasl_templates/main.py"
APP_ICON = os.path.join( BASE_DIR, "vasl_templates/webapp/static/images/app.ico" )

# ---------------------------------------------------------------------

def main( args ): #pylint: disable=too-many-locals
    """Main processing."""

    # parse the command-line options
    output_fname = None
    no_loader = False
    work_dir = None
    cleanup = True
    opts,args = getopt.getopt( sys.argv[1:], "o:w:", ["output=","no-loader","work=","no-clean"] )
    for opt, val in opts:
        if opt in ["-o","--output"]:
            output_fname = val.strip()
        elif opt in ["--no-loader"]:
            no_loader = True
        elif opt in ["-w","--work"]:
            work_dir = val.strip()
        elif opt in ["--no-clean"]:
            cleanup = False
        else:
            raise RuntimeError( "Unknown argument: {}".format( opt ) )
    if not output_fname:
        raise RuntimeError( "No output file was specified." )

    # figure out where to locate our work directories
    if work_dir:
        work_dir = os.path.abspath( work_dir )
        build_dir = os.path.join( work_dir, "build" )
        if os.path.isdir( build_dir ):
            shutil.rmtree( build_dir )
        dist_dir = os.path.join( work_dir, "dist" )
        if os.path.isdir( dist_dir ):
            shutil.rmtree( dist_dir )
    else:
        build_dir = tempfile.mkdtemp()
        dist_dir = tempfile.mkdtemp()

    # figure out the format of the release archive
    formats = { ".zip": "zip", ".tar.gz": "gztar", ".tar.bz": "bztar", ".tar": "tar" }
    output_fmt = None
    for extn,fmt in formats.items():
        if output_fname.endswith( extn ):
            output_fmt = fmt
            output_fname2 = output_fname[:-len(extn)]
            break
    if not output_fmt:
        raise RuntimeError( "Unknown release archive format: {}".format( os.path.split(output_fname)[1] ) )

    # configure pyinstaller
    # NOTE: Using UPX gave ~25% saving on Windows, but failed to run because of corrupt DLL's :-/
    target_name = make_target_name( "vasl-templates" )
    args = [
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--specpath", build_dir,
        "--onefile",
        "--name", target_name,
    ]
    args.extend( [ "--add-data",
        os.path.join( BASE_DIR, "vassal-shim/release/vassal-shim.jar" + os.pathsep + "vasl_templates/webapp" )
    ] )
    # NOTE: We also need to include the config/ and data/ subdirectories, but we would like to
    # make them available to the user, so we include them ourself in the final release archive.
    def map_dir( src, dest ): #pylint: disable=missing-docstring
        args.extend( [ "--add-data",
            os.path.join( BASE_DIR, src + os.pathsep + dest )
        ] )
    map_dir( "vasl_templates/ui", "vasl_templates/ui" )
    map_dir( "vasl_templates/resources", "vasl_templates/resources" )
    map_dir( "vasl_templates/webapp/static", "vasl_templates/webapp/static" )
    map_dir( "vasl_templates/webapp/templates", "vasl_templates/webapp/templates" )
    if sys.platform == "win32":
        args.append( "--noconsole" )
        args.extend( [ "--icon", APP_ICON ] )
        # NOTE: These files are not always required but it's probably safer to always include them.
        import distutils.sysconfig #pylint: disable=import-error
        dname = os.path.join( distutils.sysconfig.get_python_lib() , "PyQt5/Qt5/bin" )
        args.extend( [ "--add-binary", os.path.join(dname,"libEGL.dll") + os.pathsep + "PyQt5/Qt/bin" ] )
        args.extend( [ "--add-binary", os.path.join(dname,"libGLESv2.dll") + os.pathsep + "PyQt5/Qt/bin" ] )
    args.append( MAIN_SCRIPT )

    # freeze the application
    start_time = time.time()
    os.chdir( BASE_DIR )
    run_pyinstaller( args ) # nb: this doesn't return any indication if it worked or not :-/

    # add extra files to the distribution
    def ignore_files( dname, fnames ): #pylint: disable=redefined-outer-name
        """Return files to ignore during copytree()."""
        # ignore cache files
        ignore = [ "__pycache__", "GPUCache" ]
        # ignore dot files
        ignore.extend( f for f in fnames if f.startswith(".") )
        # ignore Python files
        ignore.extend( f for f in fnames if os.path.splitext(f)[1] == ".py" )
        # ignore anything in .gitignore
        fname = os.path.join( dname, ".gitignore" )
        if os.path.isfile( fname ):
            with open( fname, "r", encoding="utf-8" ) as fp:
                for line_buf in fp:
                    line_buf = line_buf.strip()
                    if not line_buf or line_buf.startswith("#"):
                        continue
                    ignore.append( line_buf ) # nb: we assume normal filenames i.e. no globbing
        return ignore
    shutil.copy( "LICENSE.txt", dist_dir )
    shutil.copytree( "vasl_templates/webapp/data", os.path.join(dist_dir,"data") )
    shutil.copytree( "vasl_templates/webapp/config", os.path.join(dist_dir,"config"), ignore=ignore_files )

    # copy the examples
    dname = os.path.join( dist_dir, "examples" )
    os.makedirs( dname )
    fnames = [ f for f in os.listdir("examples") if os.path.splitext(f)[1] in (".json",".png") ]
    for f in fnames:
        shutil.copy( os.path.join("examples",f), dname )

    # set the build info
    build_info = {
        "timestamp": int( time.time() ),
    }
    build_info.update( get_git_info() )
    dname = os.path.join( dist_dir, "config" )
    fname = os.path.join( dname, "build-info.json" )
    with open( fname, "w", encoding="utf-8" ) as fp:
        json.dump( build_info, fp )

    # freeze the loader
    if no_loader:
        print( "Not including the loader." )
    else:
        print( "--- BEGIN FREEZE LOADER ---" )
        shutil.move(
            os.path.join( dist_dir, target_name ),
            os.path.join( dist_dir, make_target_name("vasl-templates-main") )
        )
        from loader.freeze import freeze_loader #pylint: disable=no-name-in-module
        freeze_loader(
            os.path.join( dist_dir, target_name ),
            build_dir, # nb: a "loader" sub-directory will be created and used
            False # nb: we will clean up, or not, everything ourself
        )

    # create the release archive
    os.chdir( dist_dir )
    print()
    print( "Generating release archive: {}".format( output_fname ) )
    shutil.make_archive( output_fname2, output_fmt )
    file_size = os.path.getsize( output_fname )
    print( "- Done: {0:.1f} MB".format( float(file_size) / 1024 / 1024 ) )

    # clean up
    if cleanup:
        os.chdir( BASE_DIR ) # so we can delete the build directory :-/
        shutil.rmtree( build_dir )
        shutil.rmtree( dist_dir )

    # log the elapsed time
    elapsed_time = time.time() - start_time
    print()
    print( "Elapsed time: {}".format( datetime.timedelta( seconds=int(elapsed_time) ) ) )

# ---------------------------------------------------------------------

def get_git_info():
    """Get the git branch/commit we're building from."""

    # get the latest commit ID
    proc = subprocess.run(
        [ "git", "log" ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
        check=True
    )
    buf = proc.stdout.split( "\n" )[0]
    mo = re.search( r"^commit ([a-z0-9]+)$", buf )
    last_commit_id = mo.group(1)

    # get the current git branch
    proc = subprocess.run(
        [ "git", "branch" ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
        check=True
    )
    lines = [ s for s in proc.stdout.split("\n") if s.startswith("* ") ]
    if len(lines) != 1:
        raise RuntimeError( "Can't parse git branch status." )
    branch_name = lines[0][2:]
    if branch_name.startswith( "(HEAD detached at" ) and branch_name.endswith( ")" ):
        branch_name = branch_name[18:-1]

    return { "last_commit_id": last_commit_id, "branch_name": branch_name }

def make_target_name( fname ):
    """Generate a target filename."""
    return fname+".exe" if sys.platform == "win32" else fname

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main( sys.argv[1:] )
