import re
import os

class unexception(Exception):
	def __init__(self, description, lparanum):
		self.description = description
		self.paranum = lparanum

	def __str__(self):
		ret = ""
		if self.fragment:
			ret = ret + "Fragment: " + self.paranum + "\n\n"
		ret = ret + self.description + "\n"
		return ret


undoclinks = "../pdf/"

pdfdir = os.path.join("..", "..", "undata", "pdf")
pdfxmldir = os.path.join("..", "..", "undata", "pdfxml")
htmldir = os.path.join("..", "..", "undata", "html")
sCallScrape = None  # set by one of the

bQuiet = False
def IsNotQuiet():
	return not bQuiet
def SetQuiet(lbQuiet):
	global bQuiet
	bQuiet = lbQuiet
def SetCallScrape(lsCallScrape):
	global sCallScrape
	sCallScrape = lsCallScrape

reressplit = """(?x)(
				A/\d+/[\w\d\.]*?\d+(?:/(?:Add|Rev)\.\d+)?|
				(?:General\sAssembly\s|Economic\sand\sSocial\sCouncil\s)?resolution\s\d+/\d+|
				(?:Security\sCouncil\s)?(?:resolution\s)?\d+\s\(\d\d\d\d\)|
				</b>\s*<b>|
				</i>\s*<i>
				)(?!=\s)"""

from unscrape import ScrapePDF

def MakeCheckLink(ref, link):
	fpdf = os.path.join(pdfdir, ref + ".pdf")
	if not os.path.isfile(fpdf):
		if not sCallScrape or not ScrapePDF(ref):
			return '<a class="nolink" href="%s%s.pdf">%s</a>' % (undoclinks, ref, link)
		assert os.path.isfile(fpdf)
	return '<a href="%s%s.pdf" class="pdf">%s</a>' % (undoclinks, ref, link)

def MarkupLinks(paratext, paranum):
	stext = re.split(reressplit, paratext)
	res = [ ]
	for st in stext:   # don't forget to change the splitting regexp above
		mres = re.match("(?:General Assembly )?resolution (\d+)/(\d+)", st)
		meres = re.match("Economic and Social Council resolution (\d+)/(\d+)", st)
		mdoc = re.match("A/(\d+)/(\S*)", st)
		msecres = re.match("(?:Security Council )?(?:resolution )?(\d+) \((\d\d\d\d)\)", st)
		mcan = re.match("</b>\s*<b>|</i>\s*<i>", st)
		if mres:
			res.append(MakeCheckLink("A-RES-%s-%s" % (mres.group(1), mres.group(2)), st))
		elif meres:
			res.append(MakeCheckLink("E-RES-%s-%s" % (meres.group(1), meres.group(2)), st))
		elif mdoc:
			doccode = re.sub("/", "-", mdoc.group(2))
			res.append(MakeCheckLink("A-%s-%s" % (mdoc.group(1), doccode), st))
		elif msecres:
			if not (1945 < int(msecres.group(2)) < 2007):  # should use current document year
				print st
				raise unexception("year on resolution not possible", paranum)
			res.append(MakeCheckLink("S-RES-%s(%s)" % (msecres.group(1), msecres.group(2)), st))
		elif mcan:
			res.append(' ')
		else:
			if re.match(reressplit, st):
				print ":%s:" % st
			res.append(st)
	return "".join(res)




# used for exceptions and for generating ids
class paranumC:
	def __init__(self, undocname, sdate, pageno, paragraphno, textcountnumber):
		self.undocname = undocname
		self.undocnamegid = re.sub("[\.\-]", "", undocname)
		self.sdate = sdate
		self.pageno = pageno
		self.paragraphno = paragraphno
		self.textcountnumber = textcountnumber

	def MakeGid(self):
		return "doc%s-pg%03d-bk%02d" % (self.undocnamegid, int(self.pageno), self.blockno)
