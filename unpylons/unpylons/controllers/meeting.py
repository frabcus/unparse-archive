import os
import logging
import sys
import re

from unpylons.lib.base import *

import unpylons.model as model

htmldir = os.path.join(model.undatadir, "html")

log = logging.getLogger(__name__)

def WebcastLink(body, wcdate):
    #    elif hmap["pagefunc"] == "webcastindex":
    #    WriteWebcastIndexPage(hmap["body"], hmap["date"])

    if body == "securitycouncil" and wcdate >= "2003-01-09":
        return "kkk"# return EncodeHref({"pagefunc":"webcastindex", "body":"securitycouncil", "date":wcdate})
    if body == "generalassembly" and wcdate >= "2003-07-03":
        return "kkk"# return EncodeHref({"pagefunc":"webcastindex", "body":"generalassembly", "date":wcdate})
    return ""

#from quickskins import WebcastLink

rdivspl = '<div class="([^"]*)"(?: id="([^"]*)")?(?: agendanum="([^"]*)")?>(.*?)</div>(?s)'
rcouncilattendee = '<p id="[^"]*"><span class="name">([^<]*)</span>(?:\s*<span class="name">([^<]*)</span>)?\s*<span class="nation">([^<]*)</span>\s*<span class="place">(president|member)</span></p>'
respek = '<h3 class="speaker"> <span class="name">([^<]*)</span>(?: <span class="(nation|non-nation)">([^<]*)</span>)?(?: <span class="language">([^<]*)</span>)? </h3>'
monthnames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

class MeetingController(BaseController):

    def GetHtml(self, docid):
        fhtml = os.path.join(htmldir, docid + ".html")
        try:
            fin = open(fhtml)
            res = fin.read()
            fin.close()
            res = res.decode('latin1')
        except Exception, e:
            res = "Exception: " + str(e)
        return res

    def GetCdocattr(self, ftext):
        mdata = re.search('<span class="code">([^<]*)</span>\s*<span class="date">([^<]*)</span>\s*<span class="time">([^<]*)</span>\s*<span class="rosetime">([^<]*)</span>', ftext)

        sdate = mdata.group(2)
        ndate = int(sdate[8:10])
        nmonth = int(sdate[5:7])
        longdate = '%d %s %s' % (ndate, monthnames[nmonth - 1], sdate[:4])
        wikidate = '[[%d %s]] [[%s]]' % (ndate, monthnames[nmonth - 1], sdate[:4])

        webcastlink = WebcastLink("securitycouncil", sdate)
        docid = mdata.group(1)
        meetingnumber = docid[5:]
        wikirefname = "UN_" + re.sub("[\(\-\)\.]", "", docid).upper()

        return { "gid":"pg000-bk00", "docid":docid, "meetingnumber":meetingnumber, 
                 "date":sdate, "time":mdata.group(3), "rosetime":mdata.group(4), 
                 "longdate":longdate, "wikidate":wikidate, "wikirefname":wikirefname, "webcastlink":webcastlink, "basehref":"/" }
        

    # this pulls out just the ids.  we need properties and meeting numbers
    def GetPrevNextLinks(self, docid):
        currmeeting = model.Meeting.query.filter_by(docid=docid).first()
        prevmeeting = model.Meeting.query.filter_by(next_docid=docid).first()
        return prevmeeting and prevmeeting.docid, currmeeting and currmeeting.next_docid

    def ParseBodyText(self, ftext, href):
        c.bodytext = [ ]
        bkeeping = not href  # the way we slice out the speeches of one agenda
        for mdiv in re.finditer(rdivspl, ftext):
            fclass = mdiv.group(1)
            fblock = mdiv.group(4)
            fgid = mdiv.group(2)
            fagendanum = mdiv.group(3)  # only with subheadings in GA

            # the slicing operation
            if href and fclass == "subheading":
                bkeeping = (href == fgid)
            if not bkeeping:
                continue

            if fclass == "subheading":
                paragraphs = re.findall('<(?:blockquote.*?|p)[^>]*?id="([^"]*)">(.*?)</(?:blockquote|p)>', fblock)
                agendanums = fagendanum and fagendanum.split(",")
                c.bodytext.append({"divclass":"subheading", "gid":fgid, "agendanums":agendanums, "paragraphs":paragraphs}) # fix axt

            elif fclass == "council-attendees":
                for mscmember in re.finditer(rcouncilattendee, fblock):
                    name = mscmember.group(1)
                    if mscmember.group(2):
                        name = name + ", " + mscmember.group(2)
                    nation = model.Member.query.filter_by(name=mscmember.group(3)).first()
                    m = { "name":name, 'nation':nation }
                    if mscmember.group(4) == "president":
                        c.councilpresident = m
                    else:
                        c.councilattendees.append(m)

            elif fclass == "council-agenda":
                c.councilagenda = re.sub("</?p[^>]*>", "", fblock)

            elif fclass == "spoken":
                mspek = re.search(respek, fblock)

                spoketext = fblock[mspek.end(0):]
                paragraphs = re.findall('<(?:blockquote.*?|p) id="([^"]*)">(.*?)</(blockquote|p)>', spoketext)
                speakername, nationtype, speakernation = mspek.group(1), mspek.group(2), mspek.group(3)
                
                if speakernation:
                    nation = model.Member.query.filter_by(name=speakernation).first()
                elif c.body == "SC" and speakername == "The President":
                    nation = c.councilpresident["nation"]
                else:
                    nation = None
                
                if nation:
                    flagof = nation.flagof
                elif re.match("The Secretary-General", speakername):
                    flagof = "Flag_of_United_Nations.png"
                elif c.body == "GA" and re.match("The (?:Acting |Temporary )?President|The Secretary-General", speakername):
                    flagof = "Flag_of_United_Nations.png"
                else:
                    flagof = "Flag_of_Unknown.png"
                
                
                c.bodytext.append({"divclass":"speech", "gid":fgid, "speakername":speakername, "nation":nation, 
                                   "nationtype":mspek.group(2), "speakernation":speakernation, "flagof":flagof, 
                                   "language":mspek.group(4), "paragraphs":paragraphs, "spoketext":spoketext })
                
            elif fclass == "italicline":
                paragraphs = re.findall('<(?:blockquote.*?|p) id="([^"]*)">(.*?)</(blockquote|p)>', fblock)
                c.bodytext.append({"divclass":"italicline", "gid":fgid, "paragraphs":paragraphs})

            elif fclass == "recvote":
                votes = re.findall('<span class="([^"]*)">([^<]*)</span', fblock)
                paragraphs = re.findall('<p class="motiontext" id="([^"]*)">(.*?)</(p)>', fblock)  # only one of them
                mvotecount = re.search('<p class="votecount" id="[^"]*">(favour=\d+ against=\d+ abstain=\d+ absent=\d+)</p>', fblock)
                c.bodytext.append({"divclass":"recvote", "gid":fgid, "votes":votes, "paragraphs":paragraphs, "votecount":mvotecount.group(1)})

            elif fclass == "end-document":
                pass

            else:
                pass

    
    def documentmeeting(self, docid, href):
        document = model.Document.query.filter_by(docid=docid).first()
        if not document:
            return "No document " + docid
        if not document.docmodifiedtime:
            response.status_int = 302
            response.headers['location'] = h.url_for('documentspec', docid=docid)
            return 'Moved temporarily: <a href="%s">%s</a>' % (response.headers['location'], response.headers['location'])
        
        ftext = self.GetHtml(docid)
        if re.match("Exception:", ftext):
            return ftext

        c.document = document
        c.body = document.body
        if document.body == "SC":
            c.longbody = "Security Council"
            c.session, c.meeting = None, document.meetings[0].meetingnumber
    
            c.councilattendees = [ ]
            c.councilagenda = None
            c.councilpresident = None
            c.href = ""
            c.prevmeetingid, c.nextmeetingid = self.GetPrevNextLinks(docid)  # fix
    
        else:
            c.longbody = "General Assembly"
            c.session, c.meeting = document.session, document.meetings[0].meetingnumber
            c.prevmeetingid, c.nextmeetingid = self.GetPrevNextLinks(docid)  # fix
            c.href = href
        
        c.cdocattr = self.GetCdocattr(ftext)
        self.ParseBodyText(ftext, href)
        return render('scmeeting')
    

    def scmeeting(self, scmeetingnumber):
        docid = "S-PV-" + scmeetingnumber
        return self.documentmeeting(docid, "")
    
    def gameeting(self, session, meeting):
        docid = "A-%s-PV.%s" % (session, meeting)
        return self.documentmeeting(docid, "")

    def gameetinghref(self, session, meeting, href):
        docid = "A-%s-PV.%s" % (session, meeting)
        return self.documentmeeting(docid, href)

