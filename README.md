# wmg_pandoc

Files for the new WMG teaching template to be used with pandoc.

- Beamer LaTeX template files for use with md -> pandoc -> pdf.
- Powerpoint template files for md -> pandoc -> pptx.

Additional pandoc filters.

## Usage

Clone as a submodule of your project.

Example project structure.

``` ascii
resource\
  references.bib
wmg_pandoc\
  wmg_new.latex
slides\
  example.pdf
src\
  example.md
```

```bash
cd wmg_pandoc
pandoc --from=markdown+rebase_relative_paths \
       --to=beamer+smart \
       --template=wmg_new.latex \
       --filter=graphviz \
       --filter=pandoc-imagecrop \
       --slide-level=2 \
       --resource-path=../resource \
       --metadata include-resources=../src \
       --citeproc \
       ../src/example.md \
       --output=../slides/example.pdf
```

## Example

```md
---
title: Example
subtitle: Pandoc example
institute: "University of Warwick"
classoption:
- aspectratio=169
bibliography: references.bib
date: \today
---

# Introduction

## Topics

Lorem Ipsum is simply dummy text of the printing and typesetting industry. 

- Lorem Ipsum has been the industry's standard dummy text ever since the 1500s. 
- It has survived not only five centuries.
  - But also the leap into electronic typesetting.

## Consolodation

It is a long established fact that a reader will be distracted by the readable content of a page when looking at its layout. 

- The point of using Lorem Ipsum is that it has a more-or-less normal distribution of letters.
- As opposed to using 'Content here, content here', making it look like readable English. 

## References {.allowframebreaks}
```
