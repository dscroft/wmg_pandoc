#!/usr/bin/env python3

# declare function that takes a file as argument
# and converts it to a pdf file
# using pandoc
import glob
import os
from os.path import join as opj
import subprocess
import sys
import re
import shutil
import logging
import getopt
from colorama import Fore, Style

rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

def pandoc(markdownfile, mode):#
    """ Run pandoc on the given markdown file in the specified mode.
        mode can be one of:
          - accessible: generate an accessible HTML version
          - present: generate a beamer presentation without notes
          - notes: generate a beamer presentation with notes

        Beamer output is generated to .tex instead of .pdf directory
        to avoid multiple runs of pdflatex during development.
    """

    logging.info("Running pandoc on %s in %s mode", markdownfile, mode)
    
    filename = os.path.splitext(os.path.basename(markdownfile))[0] 

    pandoc_defaults = ["pandoc", 
                       "--from=markdown+rebase_relative_paths", 
                        f"--resource-path={opj(rootdir, 'resource')}",
                        f"--metadata=include-resources:{opj(rootdir, 'src')}",
                        "--filter=pandoc-include",
                        "--filter=graphviz",
                        "--filter=pandoc-imagecrop",
                        "--filter=pandoc-attribution",
                        "--filter=pandoc-include-code",
                        "--highlight-style=pygments.theme",
                        "--variable=lang=en-UK",
                        "--citeproc" ]
    
    # pandoc --list-highlight-styles
    # pandoc -o pygments.theme --print-highlight-style=pygments

    beamer_defaults = ["--to=beamer+smart", 
                       f"--template={opj(rootdir, 'wmg_pandoc', 'wmg_new.latex')}", 
                       "--slide-level=2",
                       "--variable=colorlinks=true"]
    
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
    logging.debug("Create directory %s", outdir)
    os.makedirs(outdir, exist_ok=True)
    

    logging.debug("Running command: %s", ' '.join(pandoc_cmds[mode]))
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
    logging.info("Running LaTeX on %s", texfile)

    latex_defaults = ["pdflatex", 
                      "-interaction=nonstopmode",          
                      "-halt-on-error",
                      "-shell-escape",
                      f"-output-directory={os.path.dirname(texfile)}",
                      texfile]
    
    logging.debug("Running command: %s", ' '.join(latex_defaults))
    popen = subprocess.Popen(latex_defaults, cwd=opj(rootdir,"wmg_pandoc"), 
                              universal_newlines=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.STDOUT)

    lines = [i.rstrip("\n") for i in iter(popen.stdout.readline, "")]
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, latex_defaults, lines)
    
    return os.path.splitext(texfile)[0] + ".pdf"

def move(src, dst):
    logging.info("Moving %s to %s", src, dst)

    logging.debug("Create directory %s", os.path.dirname(dst))
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    if os.path.isdir(dst):
        logging.debug("%s is a directory, appending filename", dst)
        dst = os.path.join(dst, os.path.basename(src))

    shutil.move(src, dst)


def generate(markdownfile, mode, loop_num=1):
    """ Generate the specified output from the given markdown file.
        mode can be one of:
          - accessible: generate an accessible HTML version 
          - present: generate a beamer presentation without notes
          - notes: generate a beamer presentation with notes
        loop_num specifies how many times to run LaTeX to resolve references
    """

    # check if the file exists
    if not os.path.isfile(markdownfile):
        print(f"{markdownfile} does not exist", file=sys.stderr)
        raise FileNotFoundError(markdownfile)

    try:
        if mode == "accessible":
            pandoc(markdownfile, mode)
        elif mode in ("notes", "present"):
            texfile = pandoc(markdownfile, mode)
            for i in range(loop_num):
                logging.debug("LaTeX run %d of %d", i+1, loop_num)
                pdf_file = latex(texfile)
            move(pdf_file, opj(rootdir, mode))
    except subprocess.CalledProcessError as e:
        logging.debug("Error running command: %s", " ".join(e.cmd))
        if isinstance(e.output, list) and e.output:
            for line in e.output[-30:]:
                logging.error( line )
        return True


def find_files(markdownfile, searchdir):
    # regex = r"!include\s*([a-zA-Z0-9_.\/\-]+"+re.escape(markdownfile)+r")"
    regex = r"!include\s+(.*"+re.escape(markdownfile)+r")"
    reg = re.compile(regex)

    files = []
    for filename in glob.glob(opj(searchdir, "**", "*.md"), recursive=True):
        print( filename )
        with open(filename, "r", encoding="utf-8") as f:
            matches = reg.findall(f.read())
            if matches:
                files.append(os.path.basename(filename))
                
    return files


def main():
    # Default logging level
    loglevel = logging.INFO

    loop_num = 1

    # Parse command line options for -d / --debug
    opts, args = getopt.getopt(sys.argv[1:], "dl:", ["debug", "loop="])
    for opt, val in opts:
        if opt in ("-d", "--debug"):
            loglevel = logging.DEBUG
        elif opt in ("-l", "--loop"):
            loop_num = int(val)

    logging.basicConfig(level=loglevel)

    if len(args) < 1:
        print("Usage: python3 build.py [-d|--debug] <file.md> [version]")
        return 1

    markdownfile = args[0]
    version = args[1] if len(args) > 1 else "notes"

    files = [markdownfile]
    # specified file exists in the src directory then gen that file,
    # otherwise assume that it is in a subdirectory and search for the parent md file
    # that contains it and generate that file

    while files != []:
        currentfile = opj(rootdir, "src", files[0])

        if os.path.isfile(currentfile):
            print( f"Generating {currentfile}..." )
            if generate(currentfile, version, loop_num):
                print( f"{Fore.RED}Error.{Style.RESET_ALL}" )
                break
        else:
            print( f"Searching for {files[0]}..." )
            files += find_files(files[0], opj(rootdir, "src"))
        
        files.pop(0)

    print( f"{Fore.GREEN}Done.{Style.RESET_ALL}" )

if __name__ == "__main__":
    sys.exit(main())

