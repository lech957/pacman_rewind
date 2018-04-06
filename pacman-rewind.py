#!/bin/python3

#pacman-rewind
import os
import re
import sys


# argument stuff ##########################################
#TODO use existing module instead e.g. argparse
class Arguments:
    def __init__(self, args):
        self.args = {}
        self.options=[]
        for a in args:
            t = a.split('=')
            if len(t)==1:
                self.options.append(t[0].strip('-'))
            elif len(t)==2:
                self.args[t[0].strip('-')]=t[1]
            elif len(t)>2:
                self.args[t[0].strip('-')] = "=".join(t[1:]) # if there happens to be an equal sign within the value, just put it back there
            
    def has_option(self, oname):
        return oname in self.options
    
    def has_argument(self,  aname):
        return aname in self.args
        
    def get_argument(self, aname):
        if aname not in self.args:
            return None
        return self.args[aname]



# packageitem stuff #########################################

class PackageItem:
    def __init__(self,  name,  old_version,  new_version):
        self.name=name
        self.old_version=old_version
        self.new_version=new_version
        self.downgrade_file=""
        self.downgradable=False
    def __str__(self):
        return self.extract_pure_package_name() + " -> " + self.downgrade_file
        
    # extract just the name of the name versions combination
    def extract_pure_package_name(self):
        return self.name[:self.name.find("(")-1]
    def set_downgrade_file(self, filepath):
        if filepath==None:
            self.downgradable=False
            self.downgrade_file=""
        else:
            self.downgradable=True
            self.downgrade_file=filepath
        
# main stuff ###############################################



def find_last_upgrade(lines):
    pattern1=" [PACMAN] Running 'pacman -Su'"
    pattern2=" [PACMAN] Running 'pacman -Syu'"
    for l in reversed(lines):
        if l.endswith(pattern1) or l.endswith(pattern2):
            return l
    return None

def is_last_upgrade_line(l):
    return l.endswith(" [ALPM] transaction completed")

#TODO check regex, seem to work strange
def get_package_name(l):
    r=re.compile(".+( \[ALPM\] upgraded )(.*)")
    m = r.match(l)
    #if len(m.groups)>1:
    return m.groups(0)[1]

def get_version_numbers(updateline):
    r = re.compile(r"\((?P<ver>.*?)\)")
    return r.search(updateline).groups()[0].split(" -> ")


def read_log_file(log_file):
    with open(log_file) as f:
        lines = f.readlines()
    lines = [l.strip('\n') for l in lines]
    return lines

# list methods
def list_last_upgrade(log_file):
    lines=read_log_file(log_file)
    last = find_last_upgrade(lines)
    res=[]
    if not(last==None):
      #  print("Last Ugrade: "+last)
        idx =lines.index(last)
        while idx<len(lines) and not is_last_upgrade_line(lines[idx]):
            if  "upgraded" in lines[idx]: # check if the line points to upgrades package
                res.append(get_package_name(lines[idx]))
            idx = idx+1
    return res
    

#region file methods
def get_all_package_files(dir):
    res=[]
    for f in os.listdir(dir):
        if f.endswith("pkg.tar.xz"):
            res.append(f)
    return res

#TODO: check if version number always indicate the file name
def try_get_downgrade_file(item, pkg_path,  files):
    t = item.extract_pure_package_name()+"-"+item.old_version
    for f in files:
        if f.startswith(t):
            item.set_downgrade_file(os.path.join( pkg_path, f))
            return item.downgrade_file
    item.set_downgrade_file(None)
    return None
    

# script creation methods
def get_last_upgrade_items(log_file, pkg_path):
    list = list_last_upgrade(log_file)
    files = get_all_package_files(pkg_path)
    res=[]
    for i in list:
        vs=get_version_numbers(i)
        item= PackageItem(i, vs[0], vs[1])
        try_get_downgrade_file(item,pkg_path,  files)
        res.append(item)
    return res

def generate_downgrade_script(log_file,  pkg_path):
    l=get_last_upgrade_items(log_file,  pkg_path)
    res =[]
    for n in l :
         # consider using the member
        if n.downgradable:
            res.append(n.downgrade_file)
    return  "pacman -U " + " \\\n".join(res)
    
def list_not_downgradable_packages(log_file, pkg_path):
    l=get_last_upgrade_items(log_file,  pkg_path)
    res =[]
    for n in l :
         # consider using the member
        if not n.downgradable:
            res.append(n.name)
    return res
# main method

def main(argv):
    args = Arguments(argv) 
    log_file='/var/log/pacman.log' # default path of pacman log
    pkg_path='/var/cache/pacman/pkg' # default path of pacman cache
    
    
    if args.has_option("h"):
        print("Usage")
        print("pacman-rewind.py [-l] [-n] [log=/path/to/pacman.log][pkg=/path/to/package/cache] [o=/path/to/output/script]")
        print("-l lists the last packages upgraded with '-Su' or '-Syu'")
        print("-n lists the last packages upgraded with '-Su' or '-Syu' which cannot be downgraded because of missing package in cache")
        return
    
    
    if args.has_argument("log"):
        log_file=args.get_argument("log")
        print("# use log file: "+log_file)
    if args.has_argument("pkg"):
        pkg_path=args.get_argument("pkg")
    
    if args.has_option("l"): # only list last upgrades
        print(find_last_upgrade(read_log_file(log_file)))
        print( " \n".join(list_last_upgrade(log_file)))
    elif args.has_option("n"): # only list not downgradable packes
        print("Not downgradable packages:")
        print(" \n".join(list_not_downgradable_packages(log_file, pkg_path)))
    elif args.has_argument("o"):# write to file
        print("write file.... "+args.get_argument("o"))
        with open(args.get_argument("o"), mode="w", encoding="utf-8") as f: # cannot handle short path like ~/
        #TODO fix paths
            f.write(generate_downgrade_script(log_file,pkg_path ))
    else    :
        #print("use log file: "+log_file)
        print(generate_downgrade_script(log_file,pkg_path )) # put everything to stdout

if __name__ == "__main__":
   main(sys.argv[1:])
    
    
