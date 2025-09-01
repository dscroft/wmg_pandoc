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

def generate(markdownfile, rootdir, version):
    # check if the file exists
    if not os.path.isfile(markdownfile):
        print(f"{markdownfile} does not exist", file=sys.stderr)
        return

    # check is recognised type
    versions = ("notes", "present", "accessible")
    if version == "all":
        for i in versions:
            generate(markdownfile, rootdir, i)
        return
    elif version not in versions:
        print(f"{version} is not a recognised option", file=sys.stderr)
        return

    # get the name of the file without the extension
    filename = os.path.splitext(os.path.basename(markdownfile))[0]

    # create the output directory if it does not exist
    outputdir = os.path.join(rootdir, version)
    os.makedirs(outputdir, exist_ok=True)

    filters = ["pandoc-include",
              "graphviz",
              "pandoc-imagecrop",
              "pandoc-attribution",
              "pandoc-include-code"]
    if version == "accessible":
        filters += ["pandoc-classfilter"]

    tf = opj(rootdir, "wmg_pandoc", "wmg_new.latex")
    template = {"accessible": ["--to=html", "--embed-resources", "--standalone", "--variable=maxwidth=50%"],
                "present": ["--to=beamer+smart", f"--template={tf}", "--slide-level=2"],
                "notes":   ["--to=beamer+smart", f"--template={tf}", "--slide-level=2", "--variable=notes"]}
    
    of = opj(outputdir, filename)
    output = {"accessible": f"{of}.html",
              "present":    f"{of}.pdf",
              "notes":      f"{of}.pdf"}

    command = ["pandoc", "--from=markdown+rebase_relative_paths"] + \
                template[version] + \
                [ f"--filter={i}" for i in filters ] + \
                [ f"--resource-path={opj(rootdir, 'resource')}",
                  f"--metadata=include-resources:{opj(rootdir, 'src')}",
                  "--citeproc" ] + \
                [ f"--output={output[version]}" ] + \
                [opj(rootdir, "src", markdownfile)]
    
    #print( " ".join(command) )

    popen = subprocess.Popen(command, cwd=opj(rootdir,"wmg_pandoc"), 
                              universal_newlines=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.STDOUT)

    for line in iter(popen.stdout.readline, ""):
        if line == "Created directory imagecrop-images\n": continue
        sys.stdout.write( line )
         
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, command)

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
            generate(currentfile, rootdir, version)
        else:
            print( f"Searching for {markdownfile}..." )
            files += find_files(markdownfile, rootdir)

    print( "Done." )

