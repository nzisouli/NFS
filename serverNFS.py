from os import *
from time import *
import subprocess
from socket import *
from struct import *
import argparse

files = {}
fid_counter = 0
total_fids = 2
serverSocket = None
address = None
block_size = 20


def send_back(payload):
	global serverSocket, address

	serverSocket.sendto(payload, address)


def open_file(filename, flags):
	global files, fid_counter, total_fids
	
	try:
		fd = open(filename, (flags))
		close(fd)
		opened = False
		for fid in files:
			if files[fid][0] == filename:
				opened = True
				break
		
		if opened == True:
			files[fid][2] +=1
			statinfo = stat(filename)
			size = int(statinfo.st_size)

			payload = pack('!i', fid) + pack('!i',size) + pack('!i', files[fid][2]) 
			send_back(payload)
		else:
			if len(files) == total_fids:
				i = 0
				for fid in files:
					if i == 0:
						min_time = files[fid][2]
						rem_fid = fid

					if files[fid][2] < min_time:
						min_time = files[fid][2]
						rem_fid = fid
					i += 1

				close(files[rem_fid][1])
				del files[rem_fid]

			fd = open(filename, (O_RDWR))
			files[fid_counter] = [filename, fd, 0]
			statinfo = stat(filename)
			size = int(statinfo.st_size)
			payload = pack('!i',fid_counter) + pack('!i',size) + pack('!i',files[fid_counter][2])
			send_back(payload)
			fid_counter += 1
	except Exception as e:
		error = str(e)
		payload = pack('!i',-1) + pack('!{}s'.format(len(error)),error)
		send_back(payload)


def read_file(fid, pos, size, version):
	global files

	if fid not in files:
		payload = pack('!i', -1) + pack('!{}s'.format(len("open")),"open")
		send_back(payload)
	else:
		if version != files[fid][2]:
			lseek(files[fid][1],(pos/block_size)*block_size, SEEK_SET)
			try:
				buff = read(files[fid][1], block_size)
				statinfo = stat(files[fid][0])
				size = int(statinfo.st_size)
				payload = pack('!i', 0) + pack('!i', size) +pack('!i',files[fid][2])+ pack('!i', len(buff)) + pack('!i',(pos/block_size)*block_size) +pack('!{}s'.format(len(buff)), buff)
				send_back(payload)
			except Exception as e:
				error = str(e)
				payload = pack('!i',-1) + pack('!{}s'.format(len(error)),error)
				send_back(payload)
		else:
			payload = pack('!i', 0) + pack('!i', size) +pack('!i',files[fid][2])
			send_back(payload)

def write_file(fid, pos, size, buff):
	global files

	if fid not in files:
		payload = pack('!i', -1) + pack('!{}s'.format(len("open")),"open")
		send_back(payload)
	else:
		lseek(files[fid][1], pos, SEEK_SET)
		try:
			size = write(files[fid][1], buff)
			statinfo = stat(files[fid][0])
			length = int(statinfo.st_size)
			files[fid][2] +=1
			payload = pack('!i', 0) + pack('!i', length)+pack('!i',files[fid][2]) + pack('!i', size)
			send_back(payload)
		except Exception as e:
			error = str(e)
			payload = pack('!i',-1) + pack('!{}s'.format(len(error)),error)
			send_back(payload)

def Main():
	global serverSocket, address

	parser = argparse.ArgumentParser()
	parser.add_argument('path', type=str, help='optional filename')
	args = parser.parse_args()
	if args.path is not 0:
		pass
	else:
	    print "No path given"
	    return

	#find my address
	arg ='ip route list'
	p=subprocess.Popen(arg,shell=True,stdout=subprocess.PIPE)
	data = p.communicate()
	sdata = data[0].split()
	my_address = sdata[ sdata.index('src')+1 ]

	try:
		serverSocket = socket(AF_INET, SOCK_DGRAM)
		serverSocket.settimeout(0.5)
		serverSocket.bind((my_address, 0))
	except Exception:
		print "Exception Occured"
		return

	port = serverSocket.getsockname()[1]

	#give my info
	print "========================="
	print "Port Number: ", port
	print "IP Address: ", my_address
	print "========================="

	while True:
		try:
			request, address = serverSocket.recvfrom(1024)

			if request:
				(command,) = unpack('!i', request[0:4])

				if command == 0: #Open
					(flags,) = unpack('!i', request[4:8])
					(filename,) = unpack('!{}s'.format(len(request[8:])),request[8:])
					open_file(args.path + "/" + filename, flags)
				elif command == 1: #Read
					(fid,) = unpack('!i', request[4:8])
					(pos,) = unpack('!i', request[8:12])
					(size,) = unpack('!i', request[12:16])
					(version, ) = unpack('!i', request[16:20])
					read_file(fid, pos, size, version)
				elif command == 2: #Write
					(fid,) = unpack('!i', request[4:8])
					(pos,) = unpack('!i', request[8:12])
					(size,) = unpack('!i', request[12:16])
					(buff,) = unpack('!{}s'.format(len(request[16:])),request[16:])
					write_file(fid, pos, size, buff)
		except timeout:
			pass


if __name__ == '__main__' :
    Main()