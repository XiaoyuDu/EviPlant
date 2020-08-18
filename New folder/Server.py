'''
NOTES:

This class receives metadata and checks whether or not the files are already availabe. Then it either writes them to an image or send a request for them.

The process is multithreaded.
'''

'''
TO DO:

Work on the client side. Once you get pass sending the files to the server make sure that the image is working properly.
Fragmentation should be dealt with making loop calls to the DD command using the starting and ending blocks... that we will need to get and send with the metadata
'''

import subprocess
import datetime
import os
import time
import socket
import threading
import json
from threading import Thread
from Queue import Queue
from pymongo import MongoClient

class ThreadedServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

    def listen(self):
        self.sock.listen(50)
        while True:
            client, address = self.sock.accept()
            #client.settimeout(60)   # This could be a problem with q_file_workers... the socket cannot die until done.
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def threaded_listener(self):
        t_listener = Thread(target=self.listen)
        t_listener.setDaemon(True)
        t_listener.start()
        print 'Listener thread started'

    def listenToClient(self, client, address):
        size = 4096
        db = clientDB.UCD_DF_project
        while 1:
            try:
                data = client.recv(size)
                data_loaded = json.loads(data)
                if data:
                    if type(data_loaded) is not dict:
                        response = 'Data should be json.dumps(dict)'
                        client.send(response)
                        print response + ' -- Received: ' + str(type(data_loaded))
                    else:
                        cmd = str(data_loaded.get('cmd'))
                        if cmd == 'new metadata':  # new metadata
                            #print 'Received metadata: ', data_loaded.get('sha512') #Log... show sha512 maybe?
                            q_m.put(data_loaded)
                            response = 'OK'
                            client.send(response)
                        elif cmd == 'new client q_metadata_worker':
                            response = 'Welcome new client q_metadata_worker ' + str(data_loaded.get("worker_num"))
                            print response
                            client.send(response)
                        elif cmd == 'New client q_file_worker':
                            response = 'Welcome new client q_file_worker ' + str(data_loaded.get("worker_num"))
                            print response
                            client.send(response)
                        elif cmd == 'CLIENT sending file':  # Consider using another socket for the file transmission.  {u'cmd': u'CLIENT sending file', u'filename': u'002627.jpg', u'mongo_id': u'574ece1b61b5fe06d41baf36', u'acquisition_id': u'20160601125922', u'file': u'/000/002627.jpg', u'sha512': u'b2da9e7dfddda19487c0a645f6828e084a791e658ae4d59b710fdb0098dbd6acf0a7dcd101113b728ddd9f128e31b9e9e952a87ba98731c5e8a6bed00c55f2c9'}

                            # TO DO Check again if it's in DB. It could have been inserted since the request was made.
                            client.send('send file now')
                            file_path = str(data_loaded.get('mongo_id')) + '_' + str(data_loaded.get('filename'))
                            data = client.recv(4096)
                            data_loaded = json.loads(data)
                            f = open(os.path.join(subdirectory, file_path), 'wb')
                            print 'New file: ' + file_path
                            counter = 0
                            while (data_loaded.get('cmd') == 'send'):
                                client.send('OK, send chunk')
                                l = client.recv(4096)  # chunk
                                f.write(l)
                                print '\n\nReceived:\n' + str(l)
                                data = client.recv(4096)  # cmd
                                print '\n' + data
                                data_loaded = json.loads(data)
                            client.sendall('OK, done receiving')
                            f.close()
                            print "Done Receiving -", counter
                            counter += 1

                            #   Insert new file into DB (server maintenance will check for duplicates)
                            result = db.server_files.insert_one(
                                # We could also use the original_acquisition where it came from and some other data.
                                {
                                    "filename": data_loaded.get('filename'),
                                    "client_file_path": data_loaded.get('file'),
                                    "server_file_path": file_path,  #MUST
                                    "captured_date": [datetime.datetime.now().strftime('%Y%m%d%H%M%S')],
                                    "sha512": data_loaded.get('sha512') #MUST
                                }
                            )

                            #This should be threaded
                            #   - Recover metadata_acquisition with mongo_ID and prepare cmd_list
                            cursor = db.metadata_acquisition.find({"_id": data_loaded.get('mongo_id')}).limit(1)
                            image = ""
                            start_block = 0
                            number_of_blocks = 0
                            for doc in cursor:
                                image = str(doc.get('acquisition_id')+".raw")
                                start_block = str(doc.get('start_block'))
                                number_of_blocks = str(doc.get('number_of_blocks'))
                            #   - Prepare List
                            aux1 = 'dd'
                            aux2 = 'conv=notrunc'
                            aux3 = 'if=' + file_path
                            aux4 = 'of=' + image
                            aux5 = 'bs=4096'  # This should not be hardcoded... we need to adapt to the original image size or we won't be able to get forensically sound.
                            aux6 = 'seek=' + start_block
                            aux7 = 'count=' + number_of_blocks
                            cmd_list = []
                            cmd_list.append(aux1)
                            cmd_list.append(aux2)
                            cmd_list.append(aux3)
                            cmd_list.append(aux4)
                            cmd_list.append(aux5)
                            cmd_list.append(aux6)
                            cmd_list.append(aux7)
                            q_w.put(cmd_list)
                        elif data_loaded.get('cmd') == 'Done sending metadata':
                            client.send('OK, the server is not expecting any more metadata')
                            q_m_alive[0] = False
                        elif data_loaded.get('cmd') == 'Done sending files':
                            client.send('OK, the server is not expecting any more files')
                            q_m_alive[0] = False

                else:
                    raise NameError('Client disconnected')
            except:
                client.close()
                return False


# -- FUNCTIONS --

def q_write_worker(q_w, i):  # we need some sort of security check to see that what comes in the cmd_list is safe to exec... this is dangerous. Also consider using this with multiple writers (n Hardrives)
    sock_w = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_w.connect((ip_client, port_client))
    while 1:
        try:
            q_read = q_w.get()
            #os_system_dd(q_read)
            print 'Q_W worker would call os_system_dd if it could: ',  q_read
            if (not q_w_alive and q_w.empty()):  # if queue empty and no new additions on the way break loop, kill the loop, kill the thread.
                break
        except:
            print 'Claudio... I am working on Windows so there is no DD'
        q_w.task_done()
    print 'Terminating q_metadata_worker ', i
    sock_w.close()

def os_system_dd(cmd_list):  # EXAMPLE: cmd_list = ['time', 'dd', 'if=/dev/random', 'of=/home/anand/sys_entropy_random', 'bs=1M', 'count=5']
    #with open(self.dd_logfile, "a") as myfile:  # Saves output to log.
    #    myfile.write("\n --- New command ---")
    #    self.dd_logfile.write("\n-- Executing the time dd command --\n")
    #    a = subprocess.Popen(cmd_list, stderr=self.dd_logfile)  # DD outputs to stderr
    a = subprocess.Popen(cmd_list, shell=True, stdout=subprocess.PIPE)
    a.wait()    # This is here so we don't send all commands at once and saturate the machine.
    a.communicate()

def q_metadata_worker(q_m, i):
    db = clientDB.UCD_DF_project
    metadata_entry = db.metadata_acquisition
    sock_m = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock_m.connect((ip_client, port_client))
    while 1:
        #Read from queue
        q_read = q_m.get()
        try:    # Delete useless CMD
            del q_read['cmd']
        except KeyError:
            pass

        #Insert Acquisition into DB
        insertion = metadata_entry.insert_one(q_read).inserted_id
        print 'Metadata_acquisition: \t' + str(insertion)

        # Check if it's already in MongoDB (Files_collection):
        cursor = db.server_files.find({"sha512": q_read.get('sha512')}).limit(1)    #server_files: (id, hash, if_path)
        if cursor.count() > 0:  #We already have it
            #print str(insertion) + ' is in the server DB'
            cmd_list = prepare_cmd_list(cursor, str(q_read.get('acquisition_id')+".raw"), str(q_read.get('start_block')), str(q_read.get('number_of_blocks')))
            q_w.put(cmd_list)
        else:
            #print str(insertion) + ' is NOT in the server DB'
            #       - request from client
            message = {"cmd": 'SERVER file request', "file": q_read.get('filepath'), "mongo_id": str(insertion), "filename": q_read.get('filename'), "acquisition_id": q_read.get('acquisition_id'), "sha512": q_read.get('sha512')}
            response = send_serialized_message(sock_m, message)
            if response == 'OK':
                print q_read.get('filepath') + ' has been requested'
            else:
                print response

        q_m.task_done()
        if (not q_m_alive[0] and q_m.empty()):
            break
    print 'Terminating q_metadata_worker ', i
    sock_m.close()


def prepare_cmd_list (cursor, image, start_block, number_of_blocks):    #Call this repeteadly to write fragmented files... send the block pairs with metadata.
    for doc in cursor:
        if_path = doc.get('filename')
    aux1 = 'dd'
    aux2 = 'conv=notrunc'
    aux3 = 'if=' + str(if_path)
    aux4 = 'of=' + image
    aux5 = 'bs=4096'    # This should not be hardcoded... we need to adapt to the original image size or we won't be able to get forensically sound.
    aux6 = 'seek=' + start_block
    aux7 = 'count=' + number_of_blocks
    cmd_list = []
    cmd_list.append(aux1)
    cmd_list.append(aux2)
    cmd_list.append(aux3)
    cmd_list.append(aux4)
    cmd_list.append(aux5)
    cmd_list.append(aux6)
    cmd_list.append(aux7)
    return cmd_list

def send_serialized_message(sock, data):    # Consider using encryption.
    data_string = json.dumps(data)
    try:
        sock.sendall(data_string)
        response = sock.recv(4096)
        return response
    except Exception, e:
        print 'ERROR in server' + str(e)

def wait_for_client(ip_client, port_client):
    num = 0
    sock_reach = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print 'Reaching to the client:'
    while 1:
        try:
            sock_reach.connect((ip_client, port_client))
            sock_reach.close()
            print 'The client is available.'
            break
        except Exception, e:
            print '\tTrying to reach the client. Attempt: ' + str(num)
            time.sleep(0.5)
            num += 1

def file_receiver(socket):
    counter = 0
    aux = 1
    db = clientDB.UCD_DF_project
    file_entry = db.server_files

    socket.bind(('localhost', 12345))  # Bind to the port

    socket.listen(5)  # Now wait for client connection.
    while True:
        print '--- Server ready to receive a file...'
        c, addr = s.accept()  # Establish connection with client.   See about reusing the same socket (problem with message order)
        print ' Got connection from', addr

        data = c.recv(4096)
        data_loaded = json.loads(data)  #Dictionary with file info.

        # TO DO: Check if it's already in MongoDB (Files_collection):

        c.sendall("Ok, send file now")  #Do a check to see a whole dict was received correctly?
        f = open(os.path.join(subdirectory, data_loaded.get('filename')), 'wb') #Use subfolder

        print "\tReceiving: " + data_loaded.get('filename')
        l = c.recv(4096)
        while (l):
            f.write(l)
            l = c.recv(4096)
        f.close()
        counter += 1
        print "\tDone Receiving: " + data_loaded.get('filename')
        c.send('SERVER: File received.')
        c.close()  # Close the connection

        # TO DO: Add to q_w in a new thread!

        print ' Closed connection from', addr

        # Insert Acquisition into DB
        try:
            insertion = file_entry.insert_one(data_loaded).inserted_id
            print 'New DB file entry: \t' + str(data_loaded.get('filename'))
        except Exception, e:
            print str(e)

if __name__ == "__main__":
    host_server = 'localhost'
    port_server = 5555
    ip_client = 'localhost' # We should be getting this from client greeting... but well... for now it works.
    port_client = 5556  # We should be getting this from client greeting... but well... for now it works.

    # Prepare MongoDB
    print 'Creating MongoDB new client'
    clientDB = MongoClient()

    # Receive files
    subdirectory = "Received_Files"
    try:
        os.mkdir(subdirectory)
    except Exception:
        pass
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Create a socket object
    file_receiver_worker = Thread(target=file_receiver, args=(s,))
    file_receiver_worker.setDaemon(True)
    file_receiver_worker.start()

    # Prepare write queue   (1/2)
    q_w = Queue(maxsize=0)
    q_w_num_threads = 1
    q_w_alive = [True]

    # Prepare metadata queue
    q_m = Queue(maxsize=0)
    q_m_num_threads = 5
    q_m_alive = [True]

    print 'Raising the server listener thread now'
    ThreadedServer(host_server, port_server).threaded_listener()

    # Prepare queues   (2/2)
    wait_for_client(ip_client, port_client)
    for i in range(q_m_num_threads):  # Consider raising the q_f_workers after the reading is done.
        q_m_worker = Thread(target=q_metadata_worker, args=(q_m, i))
        q_m_worker.setDaemon(True)
        q_m_worker.start()
        print '\tq_metadata worker created - ', q_m_worker.name, i + 1

    for i in range(q_w_num_threads):  # Consider raising the q_f_workers after the reading is done.
        q_w_worker = Thread(target=q_write_worker, args=(q_w, i))
        q_w_worker.setDaemon(True)
        q_w_worker.start()
        print '\tq_writer worker created - ', q_w_worker.name, i + 1


    while 1:    # Keep alive
        time.sleep(50)
