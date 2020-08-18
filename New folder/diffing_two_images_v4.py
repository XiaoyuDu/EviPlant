 #!/usr/bin/python
# Sample program or step 8 in becoming a DFIR Wizard!
# No license as this code is simple and free!
# DFIR Wizard v11 - Part 12
# Go here to learn more http://www.hecfblog.com/2015/05/automating-dfir-how-to-series-on.html
import sys
import pytsk3
import datetime
import pyewf
import argparse
import hashlib
import csv
import os
import re
import pyvmdk
import pyvhdi
import psutil



class vhdi_Img_Info(pytsk3.Img_Info):
  def __init__(self, vhdi_file):
    self._vhdi_file = vhdi_file
    super(vhdi_Img_Info, self).__init__(
        url='', type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

  def close(self):
    self._vhdi_file.close()

  def read(self, offset, size):
    self._vhdi_file.seek(offset)
    return self._vhdi_file.read(size)

  def get_size(self):
    return self._vhdi_file.get_media_size()



def directoryRecurse(filesystemObject,directoryObject, parentPath, sha1Hash):

  for entryObject in directoryObject:
      if entryObject.info.name.name in [".", ".."]:
        continue

      try:
        f_type = entryObject.info.meta.type
      except:
          print "Cannot retrieve type of",entryObject.info.name.name
          continue
        
      try:

        # parentDirectory = '/%s' % ('/'.join(parentPath))
        # fileObject = filesystemObject.open_dir(parentDirectory)
        filepath = '/%s/%s' % ('/'.join(parentPath),entryObject.info.name.name)


        if f_type == pytsk3.TSK_FS_META_TYPE_DIR:
            sub_directory = entryObject.as_directory()
            parentPath.append(entryObject.info.name.name)
            directoryRecurse(filesystemObject, sub_directory,parentPath, sha1Hash)
            parentPath.pop(-1)
            print "Directory: %s" % filepath
            

        elif f_type == pytsk3.TSK_FS_META_TYPE_REG and entryObject.info.meta.size != 0:
            searchResult = re.match(args.search,entryObject.info.name.name)
            if not searchResult:
              continue
            filedata = entryObject.read_random(0,entryObject.info.meta.size)
            md5hash = hashlib.md5()
            md5hash.update(filedata)
            sha1hash = hashlib.sha1()
            sha1hash.update(filedata)

            #put the sha1hash into a set(used to figure out if the file is different)

            sha1Hash.add(sha1hash.hexdigest())

          # in the dic, the key is sha1hash, value is the filePath(used to find out the file according to sha1hash)

            # fullFilePath = ('%s/%s' % (parentDirectory, entryObject.info.name.name)).replace('//','/')
            # dic[sha1hash.hexdigest()] = fullFilePath
            dic[sha1hash.hexdigest()] = filepath


            wr.writerow([int(entryObject.info.meta.addr),'/'.join(parentPath)+entryObject.info.name.name,datetime.datetime.fromtimestamp(entryObject.info.meta.crtime).strftime('%Y-%m-%d %H:%M:%S'),int(entryObject.info.meta.size),md5hash.hexdigest(),sha1hash.hexdigest()])

            
        elif f_type == pytsk3.TSK_FS_META_TYPE_REG and entryObject.info.meta.size == 0:

            wr.writerow([int(entryObject.info.meta.addr),'/'.join(parentPath)+entryObject.info.name.name,datetime.datetime.fromtimestamp(entryObject.info.meta.crtime).strftime('%Y-%m-%d %H:%M:%S'),int(entryObject.info.meta.size),"d41d8cd98f00b204e9800998ecf8427e","da39a3ee5e6b4b0d3255bfef95601890afd80709"])

          
      except IOError as e:
        print e
        continue
  return dic

def extractFile(imageFile,filenames):


  vhdi_file = pyvhdi.file()
  vhdi_file.open(imageFile)
  img_info = vhdi_Img_Info(vhdi_file)
  partitionTable = pytsk3.Volume_Info(img_info)
  for partition in partitionTable:
    print partition.addr, partition.desc, "%ss(%s)" % (partition.start, partition.start * 512), partition.len
    # try:
    if 'NTFS' in partition.desc:
      filesystemObject = pytsk3.FS_Info(img_info, offset=(partition.start*512))
    # except:
    #         print "Partition has no supported file system"
    #         continue
      print "File System Type Dectected ",filesystemObject.info.ftype
      directoryObject = filesystemObject.open_dir(path=dirPath)
      print "Directory:",dirPath
    outputPath = 'ex_differ_file'

  for filename in filenames:
    if not os.path.exists(outputPath):
      os.makedirs(outputPath)
    if not os.path.isdir(str(filename)):
      try:
        ex_path = ('%s/%s' % (outputPath, os.path.basename(str(filename)))).replace('//','/') 

        extractFile = open(ex_path,'w')

        fileobject = filesystemObject.open(str(filename))
        filedata = fileobject.read_random(0,fileobject.info.meta.size)
        extractFile.write(filedata)
        extractFile.close
      except IOError:
        print('cannot open', str(filename))


        
argparser = argparse.ArgumentParser(description='Hash files recursively from a forensic image and optionally extract them')
argparser.add_argument(
        '-i1', '--image1',
        dest='imagefile1',
        action="store",
        type=str,
        default=None,
        required=True,
        help='E01 to extract from'
    )

argparser.add_argument(
        '-i2', '--image2',
        dest='imagefile2',
        action="store",
        type=str,
        default=None,
        required=True,
        help='E01 to extract from'
    )

argparser.add_argument(
        '-s', '--search',
        dest='search',
        action="store",
        type=str,
        default='.*',
        required=False,
        help='Specify search parameter e.g. *.lnk'
    )


argparser.add_argument(
        '-p', '--path',
        dest='path',
        action="store",
        type=str,
        default='/',
        required=False,
        help='Path to recurse from, defaults to /'
    )
argparser.add_argument(
        '-o', '--output',
        dest='output',
        action="store",
        type=str,
        default='inventory.csv',
        required=False,
        help='File to write the hashes to'
    )

args = argparser.parse_args()
dirPath = args.path
if not args.search == '.*':
  print "Search Term Provided",args.search 
outfile = open(args.output,'w')
outfile.write('"Inode","Full Path","Creation Time","Size","MD5 Hash","SHA1 Hash"\n')
wr = csv.writer(outfile, quoting=csv.QUOTE_ALL)


# TWO SET TO KEEP THE HASH FROM DIFFERENT IMAGE
sha1Hash1 = set([])
sha1Hash2 = set([])


# DICTIONARY IS USED TO SAVE THE FILE AND ITS CORRESPOND HASH
dic = {}
dic1 = {}
dic2 = {}

#PARAMENTER
#imageFile is a image file
#sha1Hash is a empty set which is used to save the value of the hash 
#this function will return a dic which save the filename and its hash vaulue

def image_handle(imageFile, sha1Hash):

  vhdi_file = pyvhdi.file()
  vhdi_file.open(imageFile)
  img_info = vhdi_Img_Info(vhdi_file)
  partitionTable = pytsk3.Volume_Info(img_info)
  for partition in partitionTable:
    print partition.addr, partition.desc, "%ss(%s)" % (partition.start, partition.start * 512), partition.len

    if 'NTFS' in partition.desc:
      filesystemObject = pytsk3.FS_Info(img_info, offset=(partition.start*512))

      print "File System Type Dectected ",filesystemObject.info.ftype
      directoryObject = filesystemObject.open_dir(path=dirPath)
      print "Directory:",dirPath

      dic = directoryRecurse(filesystemObject, directoryObject,[], sha1Hash)

  return dic




dic1 = image_handle(args.imagefile1, sha1Hash1)
dic2 = image_handle(args.imagefile2, sha1Hash2)



sha1Hash_diff = set([])
sha1Hash_diff.update(sha1Hash1.symmetric_difference(sha1Hash2))


# V IS A LIST WHICH KEEP THE DIFF HASH
v = []
for s in sha1Hash_diff:
  v.append(dic[s]) 

print v

extractFile(args.imagefile1, v)

extractFile(args.imagefile2, v)




