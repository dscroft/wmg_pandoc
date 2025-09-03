#!/usr/bin/env python3

# declare function that takes a file as argument
# and converts it to a pdf file
# using pandoc
import cmd
import glob
import os
from os.path import join as opj
from statistics import mode
import subprocess
import sys
import re
import shutil
import logging

logging.basicConfig(level=logging.INFO)

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def pandoc(markdownfile, mode):
    logging.info(f"Running pandoc on {markdownfile} in {mode} mode")
    
    filename = os.path.splitext(os.path.basename(markdownfile))[0] 

    pandoc_defaults = ["pandoc", 
                       "--from=markdown+rebase_relative_paths", 
                        f"--resource-path={opj(rootdir, 'resource')}",
                        f"--metadata=include-resources:{opj(rootdir, 'src')}",
                        "--citeproc", 
                        "--filter=pandoc-include",
                        "--filter=graphviz",
                        "--filter=pandoc-imagecrop",
                        "--filter=pandoc-attribution",
                        "--filter=pandoc-include-code"]

    beamer_defaults = ["--to=beamer+smart", 
                       f"--template={opj(rootdir, 'wmg_pandoc', 'wmg_new.latex')}", 
                       "--slide-level=2"]
    
    html_defaults = ["--to=html", 
                     "--embed-resources", 
                     "--standalone", 
                     "--variable=maxwidth=50%", 
                     "--filter=pandoc-classfilter"]
    
    outfilename = {"accessible": opj(rootdir,'accessible',f'{filename}.html'),
                   "present": opj(rootdir,'latex','present',f'{filename}.tex'),
                   "notes": opj(rootdir,'latex','notes',f'{filename}.tex')}

    pandoc_cmds = {"accessible": pandoc_defaults + \
                                 html_defaults + \
                                 [f"--output={outfilename["accessible"]}"] + \
                                 [markdownfile],

                   "present":    pandoc_defaults + \
                                 beamer_defaults + \
                                 [f"--output={outfilename["present"]}"] + \
                                 [markdownfile],
   
                   "notes":      pandoc_defaults + \
                                 beamer_defaults + \
                                 [f"--output={outfilename["notes"]}"] + \
                                 ["--variable=notes"] + \
                                 [markdownfile]}

    # Ensure the output directory exists
    outdir = os.path.dirname(outfilename[mode])
    logging.debug(f"Create directory {outdir}")
    os.makedirs(outdir, exist_ok=True)
    

    logging.debug(f"Running command: {' '.join(pandoc_cmds[mode])}")
    popen = subprocess.Popen(pandoc_cmds[mode], cwd=opj(rootdir,"wmg_pandoc"), 
                              universal_newlines=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.STDOUT)

    for line in iter(popen.stdout.readline, ""):
        if line in ("Created directory imagecrop-images\n", "Could not create directory \"imagecrop-images\"\n"): continue
        sys.stdout.write( line )
        
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, pandoc_cmds[mode]) 

    return outfilename[mode]


def latex(texfile):
    logging.info(f"Running LaTeX on {texfile}")

    latex_defaults = ["pdflatex", 
                      "-interaction=nonstopmode",          
                      "-halt-on-error",
                      f"-output-directory={os.path.dirname(texfile)}",
                      texfile]
    
    logging.debug(f"Running command: {' '.join(latex_defaults)}")
    popen = subprocess.Popen(latex_defaults, cwd=opj(rootdir,"wmg_pandoc"), 
                              universal_newlines=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.STDOUT)
    
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, latex_defaults)
    
    return texfile[:-3] + "pdf"

def move(src, dst):
    logging.info(f"Moving {src} to {dst}")

    logging.debug(f"Create directory {os.path.dirname(dst)}")
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    if os.path.isdir(dst):
        logging.debug(f"{dst} is a directory, appending filename")
        dst = os.path.join(dst, os.path.basename(src))

    shutil.move(src, dst)


def generate(markdownfile, mode):
    # check if the file exists
    if not os.path.isfile(markdownfile):
        print(f"{markdownfile} does not exist", file=sys.stderr)
        return

    if mode == "accessible":
        pandoc(markdownfile, mode)
    elif mode in ("notes", "present"):
        move(latex(pandoc(markdownfile, mode)), opj(rootdir, mode))

    
def find_files(markdownfile, rootdir):
    reg = re.compile(f"!include\\s*([a-zA-Z0-9_.\\/\\-]+{markdownfile})")

    files = []
    for filename in glob.glob(opj(rootdir, "src", "**", "*.md"), recursive=True):
        with open(filename, "r") as f:
            matches = reg.findall(f.read())
            if matches:
                files.append(filename)
                
    return files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 build.py <file.md> [version]")
        sys.exit(1)

    markdownfile = sys.argv[1]
    version = sys.argv[2] if len(sys.argv) > 2 else "notes"

    rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    files = [markdownfile]
    # specified file exists in the src directory then gen that file,
    # otherwise assume that it is in a subdirectory and search for the parent md file
    # that contains it and generate that file
    while files != []:
        currentfile = opj(rootdir, "src", files.pop(0))

        if os.path.isfile(currentfile):
            print( f"Generating {currentfile}..." )
            generate(currentfile, version)
        else:
            print( f"Searching for {markdownfile}..." )
            files += find_files(markdownfile, rootdir)

    print( "Done." )

