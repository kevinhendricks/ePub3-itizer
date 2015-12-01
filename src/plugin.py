#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import os
import tempfile, shutil
import re

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from opf_converter import Opf_Converter
from html_namedentities import named_entities
from epub_utils import epub_zip_up_book_contents

PY2 = sys.version_info[0] == 2

if PY2:
    import Tkinter as tkinter
    import ttk as tkinter_ttk
    import Tkconstants as tkinter_constants
    import tkFileDialog as tkinter_filedialog
else:
    import tkinter
    import tkinter.ttk as tkinter_ttk
    import tkinter.constants as tkinter_constants
    import tkinter.filedialog as tkinter_filedialog

_guide_epubtype_map = {
     'acknowledgements'   : 'acknowledgments',
     'other.afterword'    : 'afterword',
     'other.appendix'     : 'appendix',
     'other.backmatter'   : 'backmatter',
     'bibliography'       : 'bibliography',
     'text'               : 'bodymatter',
     'other.chapter'      : 'chapter',
     'colophon'           : 'colophon',
     'other.conclusion'   : 'conclusion',
     'other.contributors' : 'contributors',
     'copyright-page'     : 'copyright-page',
     'cover'              : 'cover',
     'dedication'         : 'dedication',
     'other.division'     : 'division',
     'epigraph'           : 'epigraph',
     'other.epilogue'     : 'epilogue',
     'other.errata'       : 'errata',
     'other.footnotes'    : 'footnotes',
     'foreword'           : 'foreword',
     'other.frontmatter'  : 'frontmatter',
     'glossary'           : 'glossary',
     'other.halftitlepage': 'halftitlepage',
     'other.imprint'      : 'imprint',
     'other.imprimatur'   : 'imprimatur',
     'index'              : 'index',
     'other.introduction' : 'introduction',
     'other.landmarks'    : 'landmarks',
     'other.loa'          : 'loa',
     'loi'                : 'loi',
     'lot'                : 'lot',
     'other.lov'          : 'lov',
     'notes'              : '',
     'other.notice'       : 'notice',
     'other.other-credits': 'other-credits',
     'other.part'         : 'part',
     'other.preamble'     : 'preamble',
     'preface'            : 'preface',
     'other.prologue'     : 'prologue',
     'other.rearnotes'    : 'rearnotes',
     'other.subchapter'   : 'subchapter',
     'title-page'         : 'titlepage',
     'toc'                : 'toc',
     'other.volume'       : 'volume',
     'other.warning'      : 'warning'
}

_ncx_tagname_map = {
    'doctitle'   : 'docTitle',
    'docauthor'  : 'docAuthor',
    'navmap'     : 'navMap',
    'navpoint'   : 'navPoint',
    'playorder'  : 'playOrder',
    'navlabel'   : 'navLabel',
    'pagelist'   : 'pageList',
    'pagetarget' : 'pageTarget'
}

_USER_HOME = os.path.expanduser("~")

IS_NAMED_ENTITY = re.compile("(&\w+;)")

# remap any html named enities to numeric entities
def convert_named_entities(text): 
    pieces = IS_NAMED_ENTITY.split(text)
    for i in range(1, len(pieces),2):
        piece = pieces[i]
        sval = named_entities.get(piece[1:],"")
        if sval != "":
            val = ord(sval)
            piece = "&#%d;" % val
            pieces[i] =piece
    return "".join(pieces)


# the plugin entry point
def run(bk):

    manifest_properties= {}
    spine_properties = {}
    epub_types = {}

    temp_dir = tempfile.mkdtemp()
    
    # copy all files to a temporary destination folder
    # to get all fonts, css, images, and etc
    bk.copy_book_contents_to(temp_dir)

    # parse all xhtml/html files
    for mid, href in bk.text_iter():
        print("..converting: ", href, " with manifest id: ", mid)
        data, mprops, sprops, etypes = convert_xhtml(bk, mid, href)

        # store away manifest and spine properties and any links 
        # to epub:types for later use in opf3
        if len(sprops) > 0:
            spine_properties[mid] = " ".join(sprops)
        if len(mprops) > 0:
            manifest_properties[mid] = " ".join(mprops)
        if len(etypes) > 0:
            epub_types[mid] = etypes

        # write out modified file
        destdir = ""
        filename = unquote(href)
        if "/" in href:
            destdir, filename = unquote(filename).split("/")
        fpath = os.path.join(temp_dir, "OEBPS", destdir, filename)
        with open(fpath, "wb") as f:
            f.write(data.encode('utf-8'))

    print("..converting: OEBPS/content.opf")

    # now parse opf2 converting it to opf3 format
    # while merging in previously collected spine and manifest properties
    opf2 = bk.readotherfile("OEBPS/content.opf")

    opfconv = Opf_Converter(opf2, spine_properties, manifest_properties)
    guide_info = opfconv.get_guide()
    lang = opfconv.get_lang()
    opf3 = opfconv.get_opf3()

    fpath = os.path.join(temp_dir, "OEBPS", "content.opf")
    with open(fpath, "wb") as f:
        f.write(opf3.encode('utf-8'))

    # need to take info from the old opf2 guide, epub_type semantics info
    # and toc.ncx to create a valid "nav.xhtml"
    # and update it to remove any doctype
    print("..parsing: OEBPS/toc.ncx")
    doctitle, toclist, pagelist = parse_ncx(bk, temp_dir)

    # now build up a nav
    print("..creating: OEBPS/nav.xhtml")
    navdata = build_nav(doctitle, toclist, pagelist, guide_info, epub_types, lang)
    fpath = os.path.join(temp_dir, "OEBPS", "nav.xhtml")
    with open(fpath, "wb") as f:
        f.write(navdata.encode('utf-8'))

    # finally ready to build epub
    print("..creating: epub3")
    data = "application/epub+zip"
    fpath = os.path.join(temp_dir,"mimetype")
    with open(fpath, "wb") as f:
        f.write(data.encode('utf-8'))

    # ask the user where he/she wants to store the new epub
    if doctitle is None or doctitle == "":
        doctitle = "filename"
    fname = cleanup_file_name(doctitle) + "_epub3.epub"
    localRoot = tkinter.Tk()
    localRoot.withdraw()
    fpath = tkinter_filedialog.asksaveasfilename(
        parent=localRoot,
        title="Save ePub3 as ...",
        initialfile=fname,
        initialdir=_USER_HOME,
        defaultextension=".epub"
        )
    # localRoot.destroy()
    localRoot.quit()
    if not fpath:
        shutil.rmtree(temp_dir)
        print("ePub3-itizer plugin cancelled by user")
        return 0

    epub_zip_up_book_contents(temp_dir, fpath)
    shutil.rmtree(temp_dir)

    print("Output Conversion Complete")
    # Setting the proper Return value is important.
    # 0 - means success
    # anything else means failure
    return 0
 
 
# convert xhtml to be epub3 friendly
#  - convert DOCTYPE
#  - add needed namespaces to html tag
#  - convert meta charset
#  - convert html named character entities to numeric entities
#  - collect any fixed layout metadata for spine page properties
#  - collect any epub:type attributes to help extend nav
#  - collect info on svg, mathml, epub:switch, and script usage for manifest properties
def convert_xhtml(bk, mid, href):
    res = []
    sproperties = []
    mproperties = []
    etypes = []
    #parse the xhtml, converting on the fly to update it
    qp = bk.qp
    qp.setContent(bk.readfile(mid))
    for text, tprefix, tname, ttype, tattr in qp.parse_iter():
        if text is not None:
            if "pre" not in tprefix:
                text = convert_named_entities(text)
            res.append(text)
        else:
            # remap doctype
            if tname == "!DOCTYPE":
                tattr['special'] = " html"

            elif tname == "html":
                tattr['xmlns:epub'] = "http://www.idpf.org/2007/ops"

            elif tname == "meta":
                mname = tattr.get("name","")
                mcontent = tattr.get("content", "")

                # determine any spine properties for this page from meta data
                # can't think of any other way to handle this
                if mname in ["layout", "orientation", "page-spread", "viewport"]:
                    if mcontent != '':
                        sproperties.append(mname+"-"+mcontent)

                # remap to new html5 charset declaration
                elif 'charset' in mcontent:
                    tattr = {}
                    tattr["charset"] = "utf-8"

            # handle manifest properties
            elif tname in ["svg", "svg:svg"] and not "svg" in mproperties:
                mproperties.append("svg")
            elif tname == "script" and "head" in tprefix and not "scripted" in mproperties:
                mproperties.append("scripted")
            elif tname in ["math", "m:math"] and not "math" in mproperties:
                mproperties.append("mathml")
            elif tname == "epub:switch" and not "switch" in mproperties:
                mproperties.append("switch")

            # build up url to epub:types mapping
            elif ttype in ["begin", "single"] and "epub:type" in tattr and "id" in tattr and "title" in tattr:
                semantic_type = tattr["epub:type"]
                id = tattr["id"]
                title = tattr["title"]
                etypes.append((href+'#'+id, semantic_type, title))

            res.append(qp.tag_info_to_xml(tname, ttype, tattr))

    return "".join(res), mproperties, sproperties, etypes


# parse the current toc.ncx to extract toc info, and pagelist info
def parse_ncx(bk, temp_dir):
    ncx_id = bk.gettocid()
    ncxdata = bk.readfile(ncx_id)
    bk.qp.setContent(ncxdata)
    pagelist = []
    toclist = []
    doctitle = None
    navlable = None
    pagenum = None
    skip_if_newline = False
    lvl = 0
    newncx =[]
    for txt, tp, tname, ttype, tattr in bk.qp.parse_iter():
        if txt is not None:
            if tp.endswith(".doctitle.text"):
                doctitle = txt
            if tp.endswith('.navpoint.navlabel.text'):
                navlabel = txt
            if skip_if_newline and txt[0:1] == '\n':
                txt = txt[1:]
            skip_if_newline = False
            newncx.append(txt)
        else:
            if tname == "navpoint" and ttype == "begin":
                lvl += 1
            elif tname == "navpoint" and ttype == "end":
                lvl -= 1
            elif tname == "content" and tattr is not None and "src" in tattr and tp.endswith("navpoint"):
                href =  tattr["src"]
                toclist.append((lvl, navlabel, href))
                navlabel = None
            elif tname == "pagetarget" and ttype == "begin" and tattr is not None:
                pagenum = tattr.get("value",None)
            elif tname == "content" and tattr is not None and "src" in tattr and tp.endswith("pagetarget"):
                pageref = tattr["src"]
                pagelist.append((pagenum, pageref))
                pagenum = None

            # remove the ncx doctype as it is no longer allowed in ncx under epub3
            if tname != "!DOCTYPE":
                if tname in _ncx_tagname_map:
                    tname = _ncx_tagname_map[tname]
                newncx.append(bk.qp.tag_info_to_xml(tname, ttype, tattr))
            else:
                skip_if_newline = True

    # overwrite modified ncx file
    data = "".join(newncx)
    filename = "toc.ncx"
    fpath = os.path.join(temp_dir, "OEBPS", filename)
    with open(fpath, "wb") as f:
        f.write(data.encode('utf-8'))
    return doctitle, toclist, pagelist


# build up nave from toclist, pagelist and old opf2 guide info for landmarks
def build_nav(doctitle, toclist, pagelist, guide_info, epub_types, lang):
    navres = []
    ind = '  '
    ibase = ind*3
    incr = ind*2
    navres.append('<?xml version="1.0" encoding="utf-8"?>\n')
    navres.append('<!DOCTYPE html>\n')
    navres.append('<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"')
    navres.append(' lang="%s" xml:lang="%s">\n' % (lang, lang))
    navres.append(ind + '<head>\n')
    navres.append(ind*2 + '<meta charset="utf-8" />\n')
    navres.append(ind*2 + '<style type="text/css">\n')
    navres.append(ind*2 + 'nav#landmarks { display:none; }\n')
    navres.append(ind*2 + 'ol { list-style-type: none; }\n')
    navres.append(ind*2 + '</style>\n')
    navres.append(ind + '</head>\n')
    navres.append(ind + '<body epub:type="frontmatter">\n')

    # start with the toc
    navres.append(ind*2 + '<nav epub:type="toc" id="toc">\n')
    navres.append(ind*3 + '<h1>Table of Contents</h1>\n')
    navres.append(ibase + '<ol>\n')
    curlvl = 1
    initial = True
    for lvl, lbl, href in toclist:
        if lvl > curlvl:
            while lvl > curlvl:
                indent = ibase + incr*(curlvl)
                navres.append(indent + "<ol>\n")
                navres.append(indent + ind + '<li>\n')
                navres.append(indent + ind*2 + '<a href="%s">%s</a>\n' % (href, lbl))
                curlvl += 1
        elif lvl <  curlvl:
            while lvl < curlvl:
                indent = ibase + incr*(curlvl-1)
                navres.append(indent + ind + "</li>\n")
                navres.append(indent + "</ol>\n")
                curlvl -= 1
            indent = ibase + incr*(lvl-1)
            navres.append(indent + ind +  "</li>\n")
            navres.append(indent + ind + '<li>\n')
            navres.append(indent + ind*2 + '<a href="%s">%s</a>\n' % (href, lbl))
        else:
            indent = ibase + incr*(lvl-1)
            if not initial:
                navres.append(indent + ind + '</li>\n')    
            navres.append(indent + ind + '<li>\n')
            navres.append(indent + ind*2 + '<a href="%s">%s</a>\n' % (href, lbl))
        initial = False
        curlvl=lvl
    while(curlvl > 0):
        indent = ibase + incr*(curlvl-1)
        navres.append(indent + ind + "</li>\n")
        navres.append(indent + "</ol>\n")
        curlvl -= 1
    navres.append(ind*2 + '</nav>\n')

    # add any existing page-list if need be
    if len(pagelist) > 0:
        navres.append(ind*2 + '<nav epub:type="page-list">\n')
        navres.append(ind*3 + '<ol>\n')
        for pn, href in pagelist:
            navres.append(ind*4 + '<li><a href="%s">%s</a></li>\n' % (href, pn))
        navres.append(ind*3 + '</ol>\n')
        navres.append(ind*2 + '</nav>\n')
    
    # use the guide from the opf2 to create the landmarks section
    navres.append(ind*2 + '<nav epub:type="landmarks" id="landmarks">\n')
    navres.append(ind*3 + '<h2>Guide</h2>\n')
    navres.append(ind*3 + '<ol>\n')
    for gtyp, gtitle, ghref in guide_info:
        etyp = _guide_epubtype_map.get(gtyp, "")
        if etyp != "":
            navres.append(ind*4 + '<li>\n')
            navres.append(ind*5 + '<a epub:type="%s" href="%s">%s</a>\n' % (etyp, ghref, gtitle))
            navres.append(ind*4 + '</li>\n')
    navres.append(ind*3 + '</ol>\n')
    navres.append(ind*2 + '</nav>\n')

    # now close it off
    navres.append(ind + '</body>\n')
    navres.append('</html>\n')
    return  "".join(navres)


# borrowed from calibre from calibre/src/calibre/__init__.py
# added in removal of non-printing chars
# and removal of . at start

def cleanup_file_name(name):
    import string
    _filename_sanitize = re.compile(r'[\xae\0\\|\?\*<":>\+/]')
    substitute='_'
    one = ''.join(char for char in name if char in string.printable)
    one = _filename_sanitize.sub(substitute, one)
    one = re.sub(r'\s', '_', one).strip()
    one = re.sub(r'^\.+$', '_', one)
    one = one.replace('..', substitute)
    # Windows doesn't like path components that end with a period
    if one.endswith('.'):
        one = one[:-1]+substitute
    # Mac and Unix don't like file names that begin with a full stop
    if len(one) > 0 and one[0:1] == '.':
        one = substitute+one[1:]
    return one

def main():
    print("I reached main when I should not have\n")
    return -1
    
if __name__ == "__main__":
    sys.exit(main())

