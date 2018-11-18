from os import *
from struct import *
from socket import *
import time

server_addr = None
cache_val = None
fds = {}
counter_fd = 0
clientSocket = None
block_size = 20
cache = {}
cache_size = 5
version = {}
#cache = {fid:[[bytes,start_pos,len],[bytes2,start_pos,len]]}

def mynfs_set_srv_addr(ipaddr, port):
	global server_addr
	global clientSocket

	server_addr = (ipaddr, port)
	try:
		clientSocket = socket(AF_INET, SOCK_DGRAM)
		clientSocket.settimeout(2)
	except Exception:
		print "Exception Occured"
		return 0

	return 1

def mynfs_set_cache_validity(secs):
	global cache_val
	cache_val = secs

def mynfs_open(fname, flags):
	global clientSocket, counter_fd
	global fds,version

	payload = pack('!i',0) + pack('!i',flags) + pack('!{}s'.format(len(fname)),fname)

	clientSocket.sendto(payload, server_addr)
	while True:
		try:
			data, server = clientSocket.recvfrom(1024)
			if data:
				(fid,) = unpack('!i', data[0:4])
				if fid >= 0:
					counter_fd += 1
					pos = 0
					(size, ) = unpack('!i', data[4:8])
					(vers,) = unpack('!i', data[8:12])
					fds[counter_fd] = [fid, pos, flags&0x00000003, fname, size]
					if fid not in cache:
						cache[fid] = []
					

					version[fid]=vers
					return counter_fd
				else:
					(error,) = unpack('!{}s'.format(len(data[4:])),data[4:])
					print error 
					return -1
		except timeout:
			clientSocket.sendto(payload, server_addr)

def mynfs_read( fd, n):
	# n is type size_t
	global clientSocket
	global fds,version
	buf = ""
	total_length = 0

	if fds[fd][2] == 2 or fds[fd][2] == 0:
		while n > 0 : #WHILE more reading must be done
			check = False
			found = False
			for i in cache[fds[fd][0]]: #for every block we have in memory
				# ++ eelgxos time stamp
				if i[1] >= fds[fd][1] and fds[fd][1] <= i[2] + i[1]:
				#if start_pos is equal or bigger than block's start_pos and smaller than it ens
					if time.time()-i[3]>=cache_val:
						found = True
						break
					if fds[fd][1]-i[1] + n > i[2]: #if we need whole block
						buf += i[0][fds[fd][1]-i[1]:i[2]]
						total_length +=i[2] - (fds[fd][1]-i[1] )
						n -= i[2] - (fds[fd][1]-i[1] )
						fds[fd][1] += i[2] - (fds[fd][1]-i[1] )
					else: #or just a piece
						buf += i[0][fds[fd][1]-i[1]:fds[fd][1]-i[1] + n]
						total_length +=n
						fds[fd][1] += n
						n = n - n
					check = True
					break
			if check == False: #if block needed not  in cache 
				#mallon vgazo ton n
				if found == False:
					payload =pack('!i',1) + pack('!i',fds[fd][0]) + pack('!i',fds[fd][1]) + pack('!i',n) + pack('!i',-1)#ask block from server
				else:
					payload =pack('!i',1) + pack('!i',fds[fd][0]) + pack('!i',fds[fd][1]) + pack('!i',n) + pack('!i',version[fds[fd][0]])#ask block from server
				clientSocket.sendto(payload, server_addr)
				while True: 
					try:
						data, server = clientSocket.recvfrom(1024)
						if data:
							(check,) = unpack('!i', data[0:4])
							if check == 0 :
								(size, ) = unpack('!i', data[4:8])
								fds[fd][4] = size
								(vers,) = unpack('!i', data[8:12])
								if found == True:
									if vers == version[fds[fd][0]]:
										i[3] = time.time()
										if fds[fd][1]-i[1] + n > i[2]: #if we need whole block
											buf += i[0][fds[fd][1]-i[1]:i[2]]
											total_length +=i[2] - (fds[fd][1]-i[1] )
											n -= i[2] - (fds[fd][1]-i[1] )
											fds[fd][1] += i[2] - (fds[fd][1]-i[1] )
										else: #or just a piece
											buf += i[0][fds[fd][1]-i[1]:fds[fd][1]-i[1] + n]
											total_length +=n
											fds[fd][1] += n
											n = n - n
										break
								version[fds[fd][0]] = vers
								cache[fds[fd][0]] = []
								(length,) = unpack('!i', data[12:16])
								(start_pos,) = unpack('!i', data[16:20])
								(block,) = unpack('!{}s'.format(len(data[20:])),data[20:])
								#epistrotfh apo to server@@!!
								#epistrofh timestamp
								if len(cache[fds[fd][0]]) == cache_size:
									min_time = cache[fds[fd][0]][0][3]
									to_del = cache[fds[fd][0]][0]
									flag = False
									for i in cache[fds[fd][0]]:
										if time.time() - i[3] > cache_val:
											cache[fds[fd][0]].remove(i)
											flag = True
										if i[3] < min_time:
											min_time = i[3]
											to_del = i
									if flag == False:
										cache[fds[fd][0]].remove(to_del)
								
								cache[fds[fd][0]].append([block,start_pos,length, time.time()])
								if fds[fd][1]-start_pos + n > length: #sees if it will read whole block
									buf += block[fds[fd][1]-start_pos:length]
									total_length +=length - (fds[fd][1]-start_pos)
									n -= length - (fds[fd][1]-start_pos)
									fds[fd][1] += length - (fds[fd][1]-start_pos)
								else:
									buf += block[fds[fd][1]-start_pos:fds[fd][1]-start_pos + n]
									total_length +=n
									fds[fd][1] += n
									n = n - n
								if length == -1 :
									print "Error: eof"
									return -1,buf
								if length < block_size :
									return total_length, buf
								break
							else: #in case of eroor
								(error,) = unpack('!{}s'.format(len(data[4:])),data[4:])
								if error == "open": # new open is needed, proceed from start
									new_fd = mynfs_open(fds[fd][3], fds[fd][2])
									cache[fds[new_fd][0]] = cache[fds[fd][0]]
									version[fds[new_fd][0]] = version[fds[fd][0]]
									fds[fd] = fds[new_fd]
									del cache[fds[fd][0]]
									del fds[new_fd]
									del version[fds[fd][0]]
									length2,block2 = mynfs_read(fd, n)
									total_length += length2
									buf += block2
									return total_length,buf
								else:
									print error + " in read"
									return -1,buf
					except timeout:
						clientSocket.sendto(payload, server_addr)
	else:
		print("Read not executable")
		return -1,buf
	return total_length,buf

def mynfs_write(fd, buf, n):
	global clientSocket
	global fds,version
	total_length = 0 #returned value of length written
	#print "Cache size: " + str(len(cache[fds[fd][0]]))
	if fds[fd][2] == 2 or fds[fd][2] == 1: #if write executable accordind to flags
		while n>0: #while theres somethin to write
			start_block=(fds[fd][1]/block_size)*block_size #find the correct block for writing

			if fds[fd][1] >= fds[fd][4]: #if we are out of file
				buf_temp = ""
				if start_block>=fds[fd][4]: #and we need a whole new block we have to "create" it
					if n<block_size: #find min bytes we need for this block
						nullby= n
					else:
						nullby = block_size
					for i in range(nullby):#"create " null buf for cache
						buf_temp = buf_temp + "\0"

					if len(cache[fds[fd][0]]) == cache_size:
									min_time = cache[fds[fd][0]][0][3]
									to_del = cache[fds[fd][0]][0]
									flag = False
									for i in cache[fds[fd][0]]:
										if time.time() - i[3] > cache_val:
											cache[fds[fd][0]].remove(i)
											flag = True
										if i[3] < min_time:
											min_time = i[3]
											to_del = i
									if flag == False:
										cache[fds[fd][0]].remove(to_del)
					cache[fds[fd][0]].append([buf_temp, start_block,len(buf_temp),time.time()])
				#else if part of buf is for a previous existing block , we ll get ttough the read fucntion
			check = False
			for i in cache[fds[fd][0]]: #for every block we have in memory
				# ++ eelgxos time stamp
				if i[1] == start_block: #if this is the block we need

					if time.time()-i[3]>=cache_val:
						break
					if n + fds[fd][1]-i[1]<= i[2]: #and our whole buff fits in the block
						temp = i[0][:fds[fd][1]-i[1]]+buf+i[0][fds[fd][1]-i[1]+n:] #put all the message in
						i[0]=temp
						total_length += n
						fds[fd][1] += n
						n = 0

					else: #else if we will put part of buf in block
						if i[2]<block_size and fds[fd][1] >= fds[fd][4]:  #we need to check if it is an out of file write
							temp_size = i[2]			#if it is ,we have to enlarge the block until the start_pos we need
							i[2]= block_size
							for k in range(fds[fd][1]-start_block - temp_size):
								i[0] = i[0]+"\0"
							temp = i[0][:fds[fd][1]-i[1]]+buf[:i[2]-(fds[fd][1]-i[1])]
						else: #else if it is a normal message within our size we procced normally
							temp = i[0][:fds[fd][1]-i[1]] + buf[:i[2]-(fds[fd][1]-i[1])]
						i[0] = temp #we change the cache block accordingly
						buf =buf[i[2]-(fds[fd][1]-i[1]):]
						n -= i[2]-(fds[fd][1]-i[1])
						total_length +=  i[2]-(fds[fd][1]-i[1])
						fds[fd][1] += i[2]-(fds[fd][1]-i[1])
						#i[2] = len(i[0])
					payload =pack('!i',2) + pack('!i',fds[fd][0]) + pack('!i',start_block) + pack('!i',block_size) + pack('!{}s'.format(len(i[0])),i[0]) #send it to server so it can change the file for everyone
					clientSocket.sendto(payload, server_addr)

					while True: #wait for server's answer
						try:
							data, server = clientSocket.recvfrom(1024)
							if data:
								(check,) = unpack('!i', data[0:4])
								if check == 0 : #we get our "ack " and nw info for the file
									(size, ) = unpack('!i', data[4:8])
									fds[fd][4] = size
									(vers,) = unpack('!i', data[8:12])
									version[fds[fd][0]] = vers
									(length,) = unpack('!i', data[12:16])
									#fds[fd][1] += length
									#!!!!!!!!!to apo kato thlei kati na kanoyme
									break
								else:
									(error,) = unpack('!{}s'.format(len(data[4:])),data[4:])
									if error == "open": #server changed the fid ,we need to get the new one
										new_fd = mynfs_open(fds[fd][3], fds[fd][2])
										cache[fds[new_fd][0]] = cache[fds[fd][0]]
										version[fds[new_fd][0]] = version[fds[fd][0]]
										fds[fd] = fds[new_fd]
										del cache[fds[fd][0]]
										del version[fds[fd][0]]
										del fds[new_fd]
										length = mynfs_write(fd, n)
										return total_length
									else:
										print error + " in write"
										return -1
						except timeout:
							clientSocket.sendto(payload, server_addr)

					check = True #we do not need a new cache block
					break

			if check == False: #if we didnt have the cache block ,we have to reach it before writing
				pos_temp = fds[fd][1]
				fds[fd][1] = start_block
				total, buf_read = mynfs_read(fd,block_size)
				fds[fd][1] =pos_temp
		return total_length
	else:
		print("Write not executable")
		return -1

def mynfs_seek( fd, pos, whence):
	temp = fds[fd][1]
	if whence == SEEK_SET :
		fds[fd][1] = pos
	elif whence == SEEK_CUR:
		fds[fd][1] = fds[fd][1] + pos
	else:
		fds[fd][1] = fds[fd][4] + pos

	if fds[fd][1] < 0:
		fds[fd][1] = temp
		return -1

	return fds[fd][1]

def mynfs_close(fd):
	if fd in fds:
		del cache[fds[fd][0]]
		del version[fds[fd][0]]
		del fds[fd]
		return 0
	else:
		return -1