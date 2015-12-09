#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

from __future__ import unicode_literals, division, absolute_import, print_function

import sys, os
from datetime import datetime

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote


def create_starttag(tname, tattr):
    tag = "<" + tname
    if tattr is not None:
        for key in tattr:
            tag += ' ' + key + '="'+tattr[key]+'"'
    tag += '>\n'
    return tag


def taginfo_toxml(taginfo):
    tname, tattr, tcontent = taginfo
    if tname is None:
        return ""
    tag = []
    tag.append('<' + tname)
    if tattr is not None:
        for key in tattr:
            tag.append(' ' + key + '="'+tattr[key]+'"' )
    if tcontent is not None:
        tag.append('>' + tcontent + '</' + tname + '>\n')
    else:
        tag.append(' />\n')
    return "".join(tag)


_epub3_allowed_dctypes = ["dictionary", "index", "distributable-object", "edupub", 
                          "preview", "teacher-edition","teacher-guide", "widget"]


_OPF_PARENT_TAGS = ['?xml', 'package', 'metadata', 'dc-metadata', 'x-metadata', 'manifest', 'spine', 'tours', 'guide']


class Opf_Converter(object):

    def __init__(self, opf2data, spine_properties, manifest_properties, mo_properties):
        self.opf = opf2data
        self.sprops = spine_properties.copy()
        self.mprops = manifest_properties.copy()
        self.moprops = mo_properties.copy()
        self.opos = 0
        self.lang = "en"
        self.title_cnt = 0
        self.creator_cnt = 0
        self.contributor_cnt = 0
        self.cover_id = None
        self.man_ids = []
        self.has_ncx = None
        self.has_pmap = None
        self.ppd = None
        self.nid = None
        self.guide = []
        self.res=[]
        self._convertOpf()


    # OPF tag iterator
    def _opf_tag_iter(self):
        tcontent = last_tattr = None
        prefix = []
        while True:
            text, tag = self._parseopf()
            if text is None and tag is None:
                break
            if text is not None:
                tcontent = text.rstrip(" \r\n")
            else: # we have a tag
                ttype, tname, tattr = self._parsetag(tag)
                if ttype == "begin":
                    tcontent = None
                    prefix.append(tname)
                    if tname in _OPF_PARENT_TAGS:
                        yield ".".join(prefix), tname, tattr, tcontent
                    else:
                        last_tattr = tattr
                else: # single or end
                    if ttype == "end":
                        prefix.pop()
                        tattr = last_tattr
                        if tattr is None:
                            tattr = {}
                        last_tattr = None
                    elif ttype == 'single':
                        tcontent = None
                    if ttype == 'single' or (ttype == 'end' and tname not in _OPF_PARENT_TAGS):
                        yield ".".join(prefix), tname, tattr, tcontent
                    tcontent = None

    # now convert the OPF from 2.0 to 3.0 
    def _convertOpf(self):
        res = []
        end_package = False
        end_metadata = False
        end_manifest = False
        end_spine = False
        end_guide = False

        for prefix, tname, tattr, tcontent in self._opf_tag_iter():

            # xmlheader
            if tname == "?xml":
                res.append('<?xml version="1.0" encoding="utf-8" standalone="no"?>\n')
                continue

            # package
            if tname == "package":
                tattr["version"] = "3.0"
                tattr["prefix"] = "rendition: http://www.idpf.org/vocab/rendition/#"
                res.append(create_starttag(tname, tattr))
                end_package = True
                continue
            
            # metadata
            if tname == "metadata":
                tattr["xmlns:dc"] = "http://purl.org/dc/elements/1.1/"
                tattr["xmlns:opf"] = "http://www.idpf.org/2007/opf"
                tattr["xmlns:dcterms"] = "http://purl.org/dc/terms/"
                res.append(create_starttag(tname, tattr))
                end_metadata= True
                continue

            
            if "metadata" in prefix and tname == "meta":
                # collect info from basic meta name value pairs if present
                if tattr.get("name","") == "cover":
                    self.cover_id = tattr.get("content",None)
                if tattr.get("name","") == "page-progression-direction":
                    self.ppd = tattr.get("content", None)

                updated_tags = self.map_meta(tname, tattr, None)
                for updated_tag in updated_tags: 
                    res.append(taginfo_toxml(updated_tag))
                continue    

            if "metadata" in prefix and tname.startswith("dc:"):
                if tname == "dc:language":
                    self.lang = tcontent
                updated_tags = self.map_dc(tname, tattr, tcontent)
                for updated_tag in updated_tags:
                    res.append(taginfo_toxml(updated_tag))
                continue

            if end_metadata and not "metadata" in prefix:
                # append the required dcterms modified information and close off metadata tag
                res.append(taginfo_toxml(["meta", {"property":"dcterms:modified"}, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")])) 

                # if there are Media Overlays properties, append the required media:* meta
                if len(self.moprops) > 0:
                    total_duration = 0.0
                    for mo_id in self.moprops:
                        mo_duration = self.moprops[mo_id]["duration"]
                        total_duration += mo_duration
                        res.append(taginfo_toxml(["meta", {"property": "media:duration", "refines": "#%s" % (mo_id)}, "%.3f" % (mo_duration)]))
                    res.append(taginfo_toxml(["meta", {"property": "media:duration"}, "%.3f" % (total_duration)]))
                    # TODO try to infer the narrator metadatum from dc:contributor?
                    #res.append(taginfo_toxml(["meta", {"property": "media:narrator"}, ""]))
                    res.append(taginfo_toxml(["meta", {"property": "media:active-class"}, "-epub-media-overlay-active"]))
                    print("..info: adding the -epub-media-overlay-active value for media:active-class")
                    res.append(taginfo_toxml(["meta", {"property": "media:playback-active-class"}, "-epub-media-overlay-playback-active"]))
                    print("..info: adding the -epub-media-overlay-playback-active value for media:playback-active-class")

                # close off metadata tag
                res.append("</metadata>\n")
                end_metadata = False
                # fall though

            # manifest
            if tname == "manifest":
                res.append("<manifest>\n")
                end_manifest = True
                continue

            # manifest items
            if prefix.endswith("manifest") and tname == "item":
                id = tattr.get("id",'')
                mtype = tattr.get("media-type","")
                self.man_ids.append(id)
                if mtype == "application/x-dtbncx+xml":
                    self.has_ncx = id
                elif mtype == "application/oebs-page-map+xml":
                    self.has_pmap = id
                if id in self.mprops:
                    tattr["properties"] = self.mprops[id]
                if id == self.cover_id:
                    cp = tattr.get("properties", None)
                    if cp is None:
                        tattr["properties"] = "cover-image"
                    else:
                        tattr["properties"] = cp + " cover-image"
                mo_id = self.mid_to_mo_id(id)
                if mo_id is not None:
                    tattr["media-overlay"] = mo_id
                res.append(taginfo_toxml((tname, tattr, None)))
                continue

            if end_manifest and not "manifest" in prefix:
                # add in as yet to be created nav document
                self.nid = "navid"
                while self.nid in self.man_ids:
                    self.nid = "x" + self.nid
                res.append('<item id="%s" media-type="application/xhtml+xml" href="nav.xhtml" properties="nav" />\n' % self.nid)
                self.man_ids.append(self.nid)
                # close off manifest
                res.append("</manifest>\n")
                end_manifest = False
                # fall though

            # spine
            if tname == "spine":
                tag = "<spine"
                if self.ppd is None:
                    self.ppd = tattr.get("page-progression-direction", None)
                if self.ppd is not None: 
                    tag += ' page-progression-direction="%s"' % self.ppd
                if self.has_ncx is not None:
                    tag += ' toc="%s"' % self.has_ncx
                if self.has_pmap is not None:
                    tag += ' page-map="%s"' % self.has_pmap
                tag += ">\n"
                res.append(tag)
                end_spine = True
                continue

            if tname == "itemref" and prefix.endswith("spine"):
                idref = tattr.get("idref", "")
                props = ""
                if "properties" in tattr:
                    props = tattr["properties"]
                if idref in self.sprops:
                    if props != "":
                        props += " " + self.sprops[idref]
                    else:
                        props = self.sprops[idref]
                if props != "":
                    tattr["properties"] = props
                res.append(taginfo_toxml((tname, tattr, None)))
                continue

            if end_spine and not "spine" in prefix:
                # add in nav document at the end of the spine
                # leave out linear (defaults to no)
                res.append('<itemref idref="%s" />\n' % self.nid)
                # close off spine
                res.append("</spine>\n")
                end_spine = False
                # fall though

            # guide
            if tname == "guide":
                # the guide is optional in epub3 so omit it
                # res.append("<guide>\n")
                end_guide = True
                continue

            # store away the guide info to be used with nav
            if tname == "reference" and  prefix.endswith("guide"):
                type = tattr.get("type",'')
                title = tattr.get("title",'')
                href = tattr.get("href",'')
                self.guide.append((type, title, href))
                # the guide is optional in epub3 so omit it
                # res.append(taginfo_toxml((tname, tattr, None)))
                continue

            if end_guide and not "guide" in prefix:
                # the guide is optional in epub3 so omit it
                # res.append("</guide>\n") 
                end_guide = False

                # also close off package since tours was deprecated in opf2 and gone from opf3 
                res.append("</package>\n")
                end_package = False
                # fall through

        if end_guide:
                # the guide is optional in epub3 so omit it
            # res.append("</guide>\n")
            end_guide = False

        if end_package:
            res.append("</package>\n")
            end_package = False

        self.res = res

        
    # parse and return either leading text or the next tag
    def _parseopf(self):
        p = self.opos
        if p >= len(self.opf):
            return None, None
        if self.opf[p] != '<':
            res = self.opf.find('<',p)
            if res == -1 :
                res = len(self.opf)
            self.opos = res
            return self.opf[p:res], None
        # handle comment as a special case
        if self.opf[p:p+4] == '<!--':
            te = self.opf.find('-->',p+1)
            if te != -1:
                te = te+2
        else:
            te = self.opf.find('>',p+1)
            ntb = self.opf.find('<',p+1)
            if ntb != -1 and ntb < te:
                self.opos = ntb
                return self.opf[p:ntb], None
        self.opos = te + 1
        return None, self.opf[p:te+1]


    # parses tag to identify:  [tname, ttype, tattr]
    #    tname: tag name,    ttype: tag type ('begin', 'end' or 'single');
    #    tattr: dictionary of tag atributes
    def _parsetag(self, s):
        n = len(s)
        p = 1
        tname = None
        ttype = None
        tattr = {}
        while p < n and s[p:p+1] == ' ' : p += 1
        if s[p:p+1] == '/':
            ttype = 'end'
            p += 1
            while p < n and s[p:p+1] == ' ' : p += 1
        b = p
        while p < n and s[p:p+1] not in ('>', '/', ' ', '"', "'","\r","\n") : p += 1
        tname=s[b:p].lower()
        # remove redundant opf prefixes
        if tname.startswith("opf:"):
            tname = tname[4:]
        # some special cases
        if tname == "?xml":
            tname = "?xml"
        if tname == "!--":
            ttype = 'single'
            comment = s[p:-3].strip()
            tattr['comment'] = comment
        if ttype is None:
            # parse any attributes of begin or single tags
            while s.find('=',p) != -1 :
                while p < n and s[p:p+1] == ' ' : p += 1
                b = p
                while p < n and s[p:p+1] != '=' : p += 1
                aname = s[b:p].lower()
                aname = aname.rstrip(' ')
                p += 1
                while p < n and s[p:p+1] == ' ' : p += 1
                if s[p:p+1] in ('"', "'") :
                    qt = s[p:p+1]
                    p = p + 1
                    b = p
                    while p < n and s[p:p+1] != qt: p += 1
                    val = s[b:p]
                    p += 1
                else :
                    b = p
                    while p < n and s[p:p+1] not in ('>', '/', ' ') : p += 1
                    val = s[b:p]
                tattr[aname] = val
        if ttype is None:
            ttype = 'begin'
            if s.find('/',p) >= 0:
                ttype = 'single'
        return ttype, tname, tattr


    # map some fixed layout tags 
    # otherwise pass old meta data through as is
    def map_meta(self, tname, tattr, tcontent):
        outtags=[]
        aname = tattr.get("name","")
        acont = tattr.get("content","")
        if aname.startswith("rendition:"):
            aname = aname[10:]
        if aname in ["orientation", "layout", "spread"]:
            nattr = {}
            nattr["property"] = "rendition:" + aname
            ncontent = acont
            outtags.append(["meta", nattr, ncontent])
            return outtags
        if aname == "fixed-layout":
            acont = acont.lower()
            if acont == "true":
                acont = "pre-paginated"
            else:
                acont = "reflowable"
            nattr = {}
            nattr["property"] = "rendition:layout"
            ncontent = acont
            outtags.append(["meta", nattr, ncontent])
            return outtags
        if aname == "orientation-lock":
            acont = acont.lower()
            if not acont in ["portrait", "landscape"]:
                acont = "auto"
            nattr = {}
            nattr["property"] = "rendition:orientation"
            ncontent = acont
            outtags.append(["meta", nattr, ncontent])
            return outtags
        outtags.append([tname, tattr, None])
        return outtags


    def map_dc(self, tname, tattr, tcontent):
        outtags = []

        if tname == "dc:title":
            self.title_cnt += 1
            id = "t%d" % self.title_cnt
            tattr["id"] = id
            outtags.append([tname, tattr, tcontent])
            if self.title_cnt==1:
                nattr = {}
                nattr["refines"] = "#" + id
                nattr["property"] = "title-type"
                outtags.append(["meta", nattr, "main"])
            return outtags

        if tname == "dc:type":
            if tcontent in _epub3_allowed_dctypes:
                outtags.append([tname,{},tcontent])
            else:
                # skip this as not an allowed epub3 type
                outtags.append([None, None, None])
            return outtags

        if tname == "dc:date":
            if tattr is not None:
               if "opf:event" in tattr or "event" in tattr:
                   event_type = tattr.get("opf:event","")
                   if event_type == "":
                       event_type = tattr.get("event","")
                   if event_type == "modification":
                       # skip this as a proper modification date will be auto added
                       outtags.append([None, None, None])
                       return outtags
                   elif event_type == "creation":
                       outtags.append(["meta",{"property":"dcterms:created"},tcontent])
                       return outtags
                   elif event_type == "publication" or event_type == "issued":
                       outtags.append(["dc:date",{},tcontent])
                       return outtags
            # only one dc:date tag is allowed and it must be publication date
            # so remove everything else
            outtags.append([None,None,None])
            return outtags

        if tname in  ["dc:creator", "dc:contributor"]:
            if tname == "dc:creator":
                self.creator_cnt += 1
                id = "create%d" % self.creator_cnt
            else:
                self.contributor_cnt += 1
                id = "contrib%d" % self.contributor_cnt
            tattr["id"] = id
            role = None
            fileas = None
            if "opf:role" in tattr:
                role = tattr["opf:role"]
                del tattr["opf:role"]
            if "opf:file-as" in tattr:
                fileas = tattr["opf:file-as"]
                del tattr["opf:file-as"]
            outtags.append([tname, tattr, tcontent])
            if role is not None:
                nattr = {}
                nattr["refines"] = "#" + id
                nattr["property"] = "role"
                nattr["scheme"] = "marc:relators"
                outtags.append(("meta", nattr, role))
            if fileas is not None:
                nattr = {}
                nattr["refines"] = "#" + id
                nattr["property"] = "file-as"
                outtags.append(["meta", nattr, fileas])
            return outtags

        if tname == "dc:identifier":
            if "opf:scheme" in tattr:
                scheme = tattr["opf:scheme"].lower()
                del tattr["opf:scheme"]
                if not tcontent.startswith("urn:") :
                    tcontent = "urn:" + scheme + ":" + tcontent
            outtags.append([tname, tattr, tcontent])
            return outtags

        # remove any opf: attributes from the remaining dc types
        if tattr is not None:
            nattr = {}
            for key in tattr:
                if not key.startswith("opf:"):
                    nattr[key] = tattr[key]
            tattr = nattr
        outtags.append([tname, tattr, tcontent])
        return outtags


    def mid_to_mo_id(self, mid):
        """
        Return the Media Overlay manifest id
        associated to the given (XHTML) manifest id,
        or None if no MO document is associated with the given manifest id.

        :param mid: manifest id
        :type  mid: str
        :rtype: str or None
        """
        for mo_id in self.moprops:
            if mid in self.moprops[mo_id]["text_ids"]:
                return mo_id
        return None

    def get_guide(self):
        return self.guide

    def get_opf3(self):
        return "".join(self.res)

    def get_lang(self):
        return self.lang
