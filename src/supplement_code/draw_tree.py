from ete3 import Tree, TreeStyle
import os

env = os.environ.copy()

# Fixed the error -- QXcbConnection: Could not connect to display
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_QPA_FONTDIR"] = env["SUPPLEMENT_APP_BIN"] + "/fonts"

text_file = open("RAxML_bipartitions.phylogeny", "r")
lines = text_file.readlines()
t=lines[0].split('\n')
t=t[0]

import ast
file = open("../../snake_tree","r")
temp=file.read()
ll=temp.split('\n')
bac_meta=list(ast.literal_eval(ll[1].split('=')[1].replace('[','').replace(']','')))  #bac_meta has the information

for i in range(0,len(bac_meta)-1):
    need_replace=bac_meta[i][0]
    replace_to=bac_meta[i][1].split('.')[0]
    t=t.replace(need_replace,replace_to)


result_tree=Tree(t)
ts = TreeStyle()
ts.show_leaf_name = True
ts.show_branch_length = True
ts.show_branch_support = True
result_tree.render("mytree.png", w=183, units="mm", tree_style=ts)
