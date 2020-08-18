#!/usr/bin/python

import datetime, paramiko, os, zipfile, shutil

import hashlib,csv

d = {}

def hash_file(filename):
   """"This function returns the SHA-1 hash
   of the file passed into it"""

   # make a hash object
   h = hashlib.sha1()

   # open file for reading in binary mode
   with open(filename,'rb') as file:

       # loop till the end of the file
       chunk = 0
       while chunk != b'':
           # read only 1024 bytes at a time
           chunk = file.read(1024)
           h.update(chunk)

   # return the hex representation of digest
   return h.hexdigest()



# Formatting Date and Creating Directory
today=datetime.date.today()-datetime.timedelta(days=3)
today=datetime.date.today()
formattedtime = today.strftime('%Y%m%d')   


from sys import platform
if platform == "darwin":
    # destination = '/Users/xiaoyu/Desktop/ex_differ_file-%s' % formattedtime
    destination = '/Users/ex_differ_file-%s' % formattedtime

elif platform == "win32":
    # destination = 'C:/ex_differ_file-%s' % formattedtime
    destination = 'C:\ex_differ_file-%s' % formattedtime



if not os.path.exists(destination):
  os.mkdir(destination)

# This function downloads the file using Paramiko
# and saves in specfied directory

def file_download(hostname, username,port, password):
# mykey = paramiko.RSAKey.from_private_key_file('~/My-ssh.priv')  # This is when password less login is setup
  password = password                                             # This is used when password is used to login      
  host = hostname
  username = username
  port = port
  transport = paramiko.Transport((host, port))
# transport.connect(username = username, pkey = mykey)        # This is when password less login is setup
  transport.connect(username = username, password = password) # This is used when password is used to login
  sftp = paramiko.SFTPClient.from_transport(transport)
  
  sftp.chdir('/home/xiaoyu')

  sftp.get('inventory.csv', 'C:\inventory.csv')

  with open('C:\inventory.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
    # print(row['Full Path'], row['SHA1 Hash'])
      d[row['SHA1 Hash']] = row['Full Path']

  # print "csv to dict"

  # print d['da39a3ee5e6b4b0d3255bfef95601890afd80709'].replace("/",os.sep)
  sftp.chdir('/home/xiaoyu/ex_differ_file')
  for filename in sftp.listdir():
      try:

      
        localpath1 = destination + os.sep + filename
        print "Downloading files ==> " + filename
        sftp.get(filename, localpath1)  
        sha1_value = hash_file(localpath1)
        print "localpath1 " + localpath1
        print "SHA1: " + sha1_value
        if d.has_key(sha1_value) and os.stat(localpath1).st_size != 0:
          d_valule = d[sha1_value].replace("/", os.sep)
          localpath2 = os.path.join("C:", os.sep, d_valule)
          # localpath2 = "C:" + os.sep + d[sha1_value]
          print "localpath2 " + localpath2
          local_dir = os.path.dirname(localpath2)

          if os.path.exists(local_dir):
            print "local_dir exists"
            # print os.access(local_dir, os.W_OK)

            if os.path.exists(localpath2):
              print "local_file eixsts"
              try:
                os.remove(localpath2)
                print "remove"
              except OSError as e:
                print "can not access" + str(e)
              
            shutil.copy(localpath1, localpath2)
            print "copy1"

          else:
            print "dir not exists"
            os.makedirs(local_dir)
            print "mkdir"
            shutil.copy(localpath1,localpath2)
            print "copy2"

 
      except IOError as e:
          print e
  sftp.close()
  transport.close()

# This function calls the file_download function 
# and moves the files to required directory. If 
# using shutil.move() then it copies permissions 
# also which is not desirable always. 

def main():

  # argparser = argparse.ArgumentParser(description='Hash files recursively from a forensic image and optionally extract them')
  argparser.add_argument(
          '-uname', '--username',
          dest='username',
          action="store",
          type=str,
          default= 'xiaoyu',
          required=True,
          help='The username to connect to server'
      )

  argparser.add_argument(
          '-pwd', '--password',
          dest='password',
          action="store",
          type=str,
          default= 'XiaoDavi',
          required=True,
          help='The password to connect to server'
      )

  argparser.add_argument(
          '-p', '--path',
          dest='path',
          action="store",
          type=str,
          default= '/home/xiaoyu/ex_differ_file',
          required=False,
          help='Path of the Evidence Package you hope to inject'
      )



  try:  
      file_download('scanlon.ucd.ie', 'xiaoyu', 22, 'XiaoDavi')
      # currentfile = os.getcwd() + '/' + 'file_%s.csv'%formattedtime    
      # shutil.copy(currentfile, destination)   
      # os.remove(currentfile)
  except Exception as e:
      print e

if __name__ == '__main__':
  main()


