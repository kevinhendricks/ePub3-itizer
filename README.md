**ePub3-itizer** is a python 3.4 or later output plugin for Sigil 
that will convert a valid epub2 epub into a valid epub3 epub.

Updated: December 15, 2020

**Very Important Note**
Support for this plugin is only provided for Sigil 1.0.0 or later. 


**How it Converts from valid epub2 to epub3**

This program walks all xhtml files doing the following:

- converting DOCTYPE to <!DOCTYPE html>
- adds epub: namespace to html tag
- converts meta charset info to be: <meta charset="utf-8">
- converts all html named character entities to numeric entities
- collects any fixed layout metadata in the head tag for opf3 spine page properties
- notes any use of svg, epub:switch, mathml, and script for opf3 manifest properties
- collects any epub:type attributes to help extend nav (landmarks) in the future

Then it reads the current opf and converts it on the fly to meet package 3 requirements

- converts package tag and adds rendition prefix information
- converting metadata it can , adding refines if need be
- passes any unknown meta tags with name/content pairs through unchanged
- adds the required dcterms modified metadata information 
- adds manifest page properties where needed including use of mathml, svg, switch, scripted and cover
- adds spine page properties where needed
- extracts the guide for use in creating the nav landmarks and removes it from opf
- adds an entry in the manifest for the new nav document
- adds the new nav document to the end of spine
    and will set it to linear="no" if an HTML TOC exists in the guide

Then it parses the current toc.ncx extracting doctitle, toc, and any pagelist 
information and removes its DOCTYPE

It then merges this with the original guide information from the opf2 
to create a new nav.xhtml file. It will now nicely handle multi-level tocs.

Finally it adds the mimetype file and zips it all up and then launches a gui 
to ask the user what to name the file and where to save it.


Please note:  Special thanks go to Alberto Pettarin who contributed all of 
the code to for handling Media Overaly metadata.  Please contact him at
http://www.albertopettarin.it/contact.html for issues realted to SMIL files.

---

Thanks also go to Doitsu, DiapDealer, and JonathanMagus and others for reporting back bugs. 
I think this code is now stable and usable. Bug reports and feature requests welcomed.


See the Sigil Plugin Index on MobileRead to find out more about this plugin and other plugins available for Sigil:
https://www.mobileread.com/forums/showthread.php?t=247431
