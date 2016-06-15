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

        
# class ewf_Img_Info(pytsk3.Img_Info):
#   def __init__(self, ewf_handle):
#     self._ewf_handle = ewf_handle
#     super(ewf_Img_Info, self).__init__(
#         url="", type=pytsk3.TSK_IMG_TYPE_EXTERNAL)

#   def close(self):
#     self._ewf_handle.close()

#   def read(self, offset, size):
#     self._ewf_handle.seek(offset)
#     return self._ewf_handle.read(size)

#   def get_size(self):
#     return self._ewf_handle.get_media_size()


def directoryRecurse(filesystemObject,directoryObject, parentPath, sha1Hash):


  # parentDirectory = '/%s' % ('/'.join(parentPath))
  # fileObject = filesystemObject.open_dir(parentDirectory)

  for entryObject in directoryObject:
      if entryObject.info.name.name in [".", ".."]:
        continue

      try:
        f_type = entryObject.info.meta.type
      except:
          print "Cannot retrieve type of",entryObject.info.name.name
          continue
        
      try:

        parentDirectory = '/%s' % ('/'.join(parentPath))
        fileObject = filesystemObject.open_dir(parentDirectory)

        if f_type == pytsk3.TSK_FS_META_TYPE_DIR:
            sub_directory = entryObject.as_directory()
            parentPath.append(entryObject.info.name.name)
            directoryRecurse(filesystemObject, sub_directory,parentPath, sha1Hash)
            parentPath.pop(-1)
            #print "Directory: %s" % filepath
            

        elif f_type == pytsk3.TSK_FS_META_TYPE_REG and entryObject.info.meta.size != 0:
            searchResult = re.match(args.search,entryObject.info.name.name)
            if not searchResult:
              continue
            filedata = entryObject.read_random(0,entryObject.info.meta.size)
            #print "match ",entryObject.info.name.name
            md5hash = hashlib.md5()
            md5hash.update(filedata)
            sha1hash = hashlib.sha1()
            sha1hash.update(filedata)

            #put the sha1hash into a set(used to figure out if the file is different)

            sha1Hash.add(sha1hash.hexdigest())

            # in the dic, the key is sha1hash, value is the filePath(used to find out the file according to sha1hash)

            fullFilePath = ('%s/%s' % (parentDirectory, entryObject.info.name.name)).replace('//','/')
            dic[sha1hash.hexdigest()] = fullFilePath

            wr.writerow([int(entryObject.info.meta.addr),
              '/'.join(parentPath)+entryObject.info.name.name,
              datetime.datetime.fromtimestamp(entryObject.info.meta.crtime).strftime('%Y-%m-%d %H:%M:%S'),
              int(entryObject.info.meta.size),
              md5hash.hexdigest(),
              sha1hash.hexdigest()])
            
        elif f_type == pytsk3.TSK_FS_META_TYPE_REG and entryObject.info.meta.size == 0:

            wr.writerow([int(entryObject.info.meta.addr),
              '/'.join(parentPath)+entryObject.info.name.name,datetime.datetime.fromtimestamp(entryObject.info.meta.crtime).strftime('%Y-%m-%d %H:%M:%S'),
              int(entryObject.info.meta.size),
              "d41d8cd98f00b204e9800998ecf8427e",
              "da39a3ee5e6b4b0d3255bfef95601890afd80709"])
          
      except IOError as e:
        print e
        continue
  return dic

def extractFile(imageFile,filenames):
  if (args.imagetype == "e01"):
    filenames = pyewf.glob(imageFile)
    ewf_handle = pyewf.handle()
    ewf_handle.open(filenames)
    imagehandle = ewf_Img_Info(ewf_handle)
  elif (args.imagetype == "raw"):
      print "Raw Type"
      imagehandle = pytsk3.Img_Info(url=imageFile)

  partitionTable = pytsk3.Volume_Info(imagehandle)
  for partition in partitionTable:
    print partition.addr, partition.desc, "%ss(%s)" % (partition.start, partition.start * 512), partition.len
    try:
          filesystemObject = pytsk3.FS_Info(imagehandle, offset=(partition.start*512))
    except:
            print "Partition has no supported file system"
            continue
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
        '-t', '--type',
        dest='imagetype',
        action="store",
        type=str,
        default=False,
        required=True,
        help='Specify image type e01 or raw'
    )
args = argparser.parse_args()
dirPath = args.path
if not args.search == '.*':
  print "Search Term Provided",args.search 
outfile = open(args.output,'w')
outfile.write('"Inode","Full Path","Creation Time","Size","MD5 Hash","SHA1 Hash"\n')
wr = csv.writer(outfile, quoting=csv.QUOTE_ALL)

sha1Hash1 = set([])
sha1Hash2 = set([])
dic = {}
dic1 = {}
dic2 = {}

def image_handle(imageFile, sha1Hash):
  if (args.imagetype == "e01"):
    filenames = pyewf.glob(imageFile)
    ewf_handle = pyewf.handle()
    ewf_handle.open(filenames)
    imagehandle = ewf_Img_Info(ewf_handle)
  elif (args.imagetype == "raw"):
      print "Raw Type"
      imagehandle = pytsk3.Img_Info(url=imageFile)

  partitionTable = pytsk3.Volume_Info(imagehandle)

  for partition in partitionTable:
    print partition.addr, partition.desc, "%ss(%s)" % (partition.start, partition.start * 512), partition.len
    try:
          filesystemObject = pytsk3.FS_Info(imagehandle, offset=(partition.start*512))
    except:
            print "Partition has no supported file system"
            continue
    print "File System Type Dectected ",filesystemObject.info.ftype
    directoryObject = filesystemObject.open_dir(path=dirPath)
    print "Directory:",dirPath

    dic = directoryRecurse(filesystemObject, directoryObject,[], sha1Hash)

  return dic



dic1 = image_handle(args.imagefile1, sha1Hash1)
dic2 = image_handle(args.imagefile2, sha1Hash2)



sha1Hash_diff = set([])
sha1Hash_diff.update(sha1Hash1.symmetric_difference(sha1Hash2))

# print'1111111111'

# print sha1Hash1
# print'2222222222'

# print sha1Hash2
# print'3333333333'
print sha1Hash_diff


# print '4444444444'
# print dic1

# print '5555555555'
# print dic2
v = []
print '6666666666'
for s in sha1Hash_diff:
  v.append(dic[s]) 

print 'vvvvvvvvvv'
print v
print 'first time'
extractFile(args.imagefile1, v)

print 'second time'
extractFile(args.imagefile2, v)




