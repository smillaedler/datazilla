from optparse import make_option
import os
from random import randint
import re

from datazilla.util.cnv import CNV
from datazilla.util.debug import D
from datazilla.util.strings import indent, outdent, between


def all_files(
    source_dir,         #DIRECTORY TO SCAN FOR PYTHON FILES
    json_file           #THE FILE OF SQL (WHO'S SQL WILL BE INSERTED AS COMMENTS)
):

    #LOAD THE JSON FILE HOLDING SQL
    json=None
    with open(json_file, 'r') as content_file:
        json=content_file.read()
        json=json.replace("\n", " ").replace("\r", "").replace("\t", "    ") #file is not real json
        json = CNV.JSON2object(json)

    #SCAN ALL PYTHON FILES
    for root, _, files in os.walk(source_dir):
        for f in files:
            fullpath = os.path.join(root, f)
            if fullpath[-3:]!='.py': continue
            content = open(fullpath, 'r').read()

            newcontent=update_comments(content, json, "query_json", "perftest")
            newcontent=update_comments(newcontent, json, "execute_json", "perftest")
            if newcontent!=content:
                D.println(newcontent)
                with open(fullpath, 'w') as outfile:
                    outfile.write(newcontent)




def has_code(python_source_line):
#RETURN TRUE IF THE SOURCE LINE HAS PYTHON CODE
    l=python_source_line.lstrip()
    return len(l)!=0 and (l.find("#")==-1 or len(l[0:l.find("#")].strip())>0)


def update_comments(content, json, method_name, project_name):
    changed=False
    start=0
    newcontent=""

    #LOOK FOR ".execute_json(" <comments> "," "\"" <name of json.sql> "\""
    for m in re.finditer(r"\."+method_name+"(\s)*\(", content):
    #for m in re.finditer(r"\.query_json(\w)*\(((\w)*#(.)*\n)*\,(\w)*\"(\W)*\"", content):
        try:
            #find first instance of (not commented) code
            last=m.end()
            for eol in [n.start()+m.end() for n in re.finditer('\n', content[m.end():])]:
                if has_code(content[last:eol]): break
                last=eol+1
            v=content[last:]

            #the name is an index into the json object
            name=between(v, "\""+project_name+".", "\"")
            o=json
            for n in name.split("."): o=o[n]

            #beautify the sql
            sql=o["sql"]
            sql=re.sub(r"((\s){5,})", r"\n\1", sql) #enough spaces means there was a cr, so we put it back in
            sql=indent(outdent(sql), "#                ")

            #assemble new comment, ignoring old
            newcontent+=content[start:m.start()]+"."+method_name+"(\n"+sql+"\n"
            start=last
            changed=True
        except Exception, e:
            pass


    newcontent+=content[start:len(content)]

    if changed: return newcontent
    return content







all_files(
    source_dir="C:\Users\klahnakoski\git\datazilla\datazilla",
    json_file="C:\Users\klahnakoski\git\datazilla\datazilla\model\sql\perftest.json"
)
