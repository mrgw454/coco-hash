
function ReplaceString$(byval source$, a$, b$)

	i = 1

    while instr(i, source$, a$) > 0
        i = instr(i, source$, a$)
        source$ = left$(source$, i-1) + b$ + mid$(source$, i + len(a$))
        i = i + len(b$)
    wend

	ReplaceString$ = source$

end function

cls

infile$ = command$

print infile$

dim xml(20) as String
t$ = Chr$(9)

open infile$ for input as #1
open "hash/coco_flop.xml" for output as #2

    print #2,"<?xml version=""1.0""?>"
    print #2,"<!DOCTYPE softwarelist SYSTEM ""softwarelist.dtd"">"
	print #2,""

	xml(1)="<softwarelist name=""coco_flop"" description=""Tandy Radio Shack Color Computer disk images"">"
	xml(2)=""

	print #2, xml(1)
	print #2, xml(2)


do until eof(1)

input #1, sha1$, crc32$, filenamewithdir$, filename$, filesize$

cls

print "--- [START} ----------"
print "Processing DSK image: " + filenamewithdir$
print ""

print "1. sha1$           : "; sha1$
print "2. crc32$          : "; crc32$
print "3. filenamewithdir$: "; filenamewithdir$
print "4. filename$       : "; filename$
print "5. filesize$       : "; filesize$
print "publisher$         : "; publisher$
print "platform$          : "; platform$
print "desc$              : "; desc$
print "descnopub$         : "; descnopub$;"<---"
print ""

filenamewithdir$ = ReplaceString(filenamewithdir$, "&", "&amp;")
filename$ = ReplaceString(filename$, "&", "&amp;")

desc$ = Right$(filenamewithdir$, Len(filenamewithdir$) - InStr(filenamewithdir$, "/")) ' trim leading folder
desc$ = Left$(desc$, InStr(desc$, "/") - 1) ' trim trailing folder

descnopub$ = Right$(filenamewithdir$, Len(filenamewithdir$) - InStr(filenamewithdir$, "/")) ' trim leading folder
descnopub$ = Left$(desc$, InStr(desc$, "(") - 2) ' trim trailing publisher

	if descnopub$ = "" then
		descnopub$ = desc$
	end if

publisher$ = Right$(desc$, Len(desc$) - InStr(desc$, "(")) ' trim text before "(" parenthesis
publisher$ = Left$(publisher$, InStr(publisher$, ")") - 1) ' trim text after ")" parenthesis

if publisher$="" then
	publisher$="unknown"
end if

platform = instr(filenamewithdir$,"(Coco 3)")

	if platform > 0 then
		platform$ = "<sharedfeat name=""compatibility"" value=""COCO3"" />"
	else
		platform$ = "<sharedfeat name=""compatibility"" value=""COCO,COCO3"" />"
	endif


name$ = Left$(filename$, InStr(filename$, ".") - 1) ' remove extension

print "1. sha1$           : "; sha1$
print "2. crc32$          : "; crc32$
print "3. filenamewithdir$: "; filenamewithdir$
print "4. filename$       : "; filename$
print "5. filesize$       : "; filesize$
print "publisher$         : "; publisher$
print "platform$          : "; platform$
print "desc$              : "; desc$
print "descnopub$         : "; descnopub$;"<---"
print "--- [END] ------------"
print ""
print ""


xml(3)=t$ + "<!-- coco (coco driver) -->"
xml(4)=t$ + "<!-- LOADM""" + name$ + """ -->"
xml(5)=t$ + "<software name=""" + name$ + """>"
xml(6)=t$ + t$ + "<description>" + descnopub$ + "</description>"
xml(7)=t$ + t$ + "<year>19xx</year>"
xml(8)=t$ + t$ + "<publisher>" + publisher$ + "</publisher>"
xml(9)=t$ + t$ + "<info name=""author"" value=""unknown"" />"
xml(10)=t$ + t$ + "<info name=""usage"" value=""LOADM &quot;" + name$ +"&quot;"" />"
xml(11)=t$ + t$ + platform$
xml(12)=t$ + t$ + "<part name=""flop0"" interface=""floppy_5_25"">"
xml(13)=t$ + t$ + t$ + "<dataarea name=""flop"" size=""" + filesize$ + """>"
xml(14)=t$ + t$ + t$ + t$ + "<rom name=""" + filename$ + """ size=""" + filesize$ + """ crc=""" + crc32$ + """ sha1=""" + sha1$ + """ offset=""0"" />"
xml(15)=t$ + t$ + t$ + "</dataarea>"
xml(16)=t$ + t$ + "</part>"
xml(17)=t$ + "</software>"
xml(18)=""

' uncomment for debug
' pause for keypress ("c")
'print "press [c] key to continue..."
'print ""

'Do
'    Sleep 1, 1
'Loop Until Inkey$ = "c"


for a = 3 to 18

	print #2, xml(a)

next a

publisher$ = ""
platform$ = ""
desc$ = ""
descnopub$ = ""

loop

	xml(19)=""
	xml(20)="</softwarelist>"

	print #2, xml(19)
	print #2, xml(20)

close #2
close #1

print ""
print "Done!"
print ""

end
