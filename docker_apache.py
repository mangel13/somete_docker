#!/usr/bin/env python
import optparse
import crypt
import M2Crypto
import string
import pwd
import operator
import os
import MySQLdb as mysql
import sys
from string import Template
import pwd
import os.path as path
import docker

#obtener nuevo uid
def n():
	all_user_data = pwd.getpwall()
	interesting_users = sorted((u
                            for u in all_user_data
                                if not u.pw_name.startswith('_') and u.pw_uid>9999 and u.pw_uid<20000),
                                        key=operator.attrgetter('pw_uid'))

	if interesting_users:
        	uid = max(u.pw_uid for u in interesting_users) + 1
	else:
        	uid=10000
	print 
	return uid



#generar passwd

def random_password(length=20):
    chars = string.ascii_uppercase + string.digits + string.ascii_lowercase+",+-_"
    password = ''
    for i in range(length):
        password += chars[ord(M2Crypto.m2.rand_bytes(1)) % len(chars)]
    return password

#crear usuario web

def createUser(name,username,password,uid):
    encPass = crypt.crypt(password,"22") 
    h=uid
    print h 
    cadena="sudo useradd -p "+str(encPass)+" -u "+h+ "   -s  /bin/false "+ "-d "+ "/storage/webs/"+name+"/home"+  " -c \""+ name+"\" " + username
    print cadena
    os.system(cadena)
    #creando home 
    os.system("zfs  create storage/webs/"+name)
    os.system("sudo zfs set quota=1G storage/webs/"+name)
    home="/storage/webs/"+name
    #os.system("mkdir "+home+"/"+dominio)
    os.system("mkdir -p "+home+"/home/tmp")
    os.system("mkdir -p "+home+"/home/read/logs")
    os.system("mkdir -p "+home+"/home/read/bak")
    os.system("mkdir -p "+home+"/home/read/bak/mysql")
    os.system("mkdir -p "+home+"/home/read/bak/app")
    os.system("mkdir -p "+home+"/conf")
    os.system("mkdir -p "+home+"/home/public_html")
    os.system("mkdir -p "+home+"/home/private")
    os.system("chown -R "+username+":"+username+" "+home)
    os.system("cp /storage/apache/conf/* "+home+"/conf/")
    """
    # añadir a /etc/exports
    l=[]
    cadena="#dominio"+name+"\n"
    l.append(cadena)
    l.append(home+"/home/read/log 10.0.11.36 (rw,sync,no_root_squash)  10.0.2.0/24  (rw,sync,no_root_squash) 10.0.11.37(rw,sync,no_root_squash)\n")
    l.append(home+"/home/public_html  10.0.11.36 (rw,sync,no_root_squash) 10.0.2.0/24  (rw,sync,no_root_squash) 10.0.11.37(rw,sync,no_root_squash)\n")
    l.append(home+"/home/private  10.0.11.36 (rw,sync,no_root_squash) 10.0.2.0/24  (rw,sync,no_root_squash) 10.0.11.37(rw,sync,no_root_squash)\n")
    with open('/etc/exports', 'a') as file:
      for linea in l:
    	file.write(linea)
    """
#crear dockerfile 

def cretaeImage(versionApache,repositorio,name,uid,dirconf):
	filein1 =open( '/storage/apache/plantillas/T-Dockerfile' )
	src = Template( filein1.read() )
        dirconf="./"
	d1={'dirconf':dirconf,'versionApache':versionApache,'uid':uid,'name':name}
	result = src.substitute(d1)
	print result
        dirdst="/storage/webs/"+name+"/conf/"
        dst=dirdst+"/Dockerfile"
	file = open(dst,'w')
	file.write(result)
        imagen=repositorio+"/"+versionApache+"_"+name 
        cmd="docker build -t "+imagen+" "+dirdst
        print cmd
        #os.system(cmd)
        #os.system(cmd2)
        return imagen
	"""
        docker build -t hamal.unizar.es:5000/5.6.30-apache_pruebas1 .
	"""
#build imagen

def buildImagei2(imagen,name,d):
        client = docker.from_env()
        p="/"+d
        image=client.images.build(tag=imagen,path=p,dockerfile="Dockerfile")
        return image

#crear container
def runImage(image,name,port_ext):
        home="/storage/webs/"+name
        data=home+"/home/public_html"
        log=home+"/home/read/logs/"
        tmp= home+"/home/tmp/"
        private=home+"/home/private"
        time="/etc/localtime"
        d=(data,log,tmp,time)={data: {'bind': '/var/www/html', 'mode': 'rw'},log: {'bind': '/var/log/apache2', 'mode': 'rw'},tmp:{'bind':'/tmp','mode':'rw'},time:{'bind':'/etc/localtime','mode':'ro'}}
        rp={"Name": "on-failure", "MaximumRetryCount": 5}
        p= {'80/tcp': port_ext} 
        mac_address="1a:2b:3c:4d:5d:6f"
        networks={"mynet123":{"external":True,"ipv4_address": "10.150.1500.130"}}
        client = docker.from_env()
        n=name+"_web"
        container = client.containers.run(image=image,volumes=d,detach=True,mem_limit="300M",cpu_shares=512,name=n,restart_policy=rp,ports=p,mac_address=mac_address,networks=networks,)
         
        #cmd= "docker run -d -v /bbdd/mysql/"+name+"/data:/var/lib/mysql  -v /bbdd/mysql/"+name+"/log:/var/log/mysql -v /bbdd/mysql/"+name+"/tmp:/tmp --env-file ./.env.lst --net mynet123 --ip "+ip+" --restart on-failure:3 --name "+name+"_mysql --blkio-weight 300 --cpu-quota=50000 -m 300M "+imagen
        #print cmd
        #os.system(cmd)       
        return container
#crear deploy swarm

def deployStack(name,imagen,pext):

	filein = open( '/storage/apache/plantillas/T-docker-compose-stack.yml' )
	src = Template( filein.read() )
	#document data
        imagen=imagen
        name=name
	vol="/storage/webs/"+name+"/home/public_html"
	vol1="/storage/webs/"+name+"/home/read/logs/"
	vol2="/storage/webs/"+name+"/home/private"

	cpu='0.5'
	mem='250M'

	cpu_r='0.001'
	mem_r='10M'
        
        networks="web_my-network1"
        ports=pext+":80"
	d={ 'name':name, 'imagen':imagen, 'vol':vol,'vol1':vol1,'vol2':vol2, 'cpu':cpu ,'mem':mem ,'cpu_r':cpu_r ,'mem_r':mem_r,'ports':ports,'networks':networks}
	#do the substitution
	result = src.substitute(d)
	print result
        dirdst="/storage/webs/"+name+"/conf/"
        dst=dirdst+"/docker-compose-stack.yml"        
        file = open(dst,'w') 
        file.write(result) 
        """
        docker stack deploy -c pruebas1.yml  web2            
        """



#tomar argumentos

parser = optparse.OptionParser()
parser.add_option("-u", "--user", dest="username",default="nouser", type="string",help="especifica el usuario")
parser.add_option("-d", "--dominio", dest="dominio", default="nodominio",type="string", help="nombre dominio")
parser.add_option("-p", "--passwd", dest="passwd", default="nopasswd",type="string", help="passwd")
parser.add_option("-c", "--dir-conf", dest="dirconf", default="/storage/apache/conf",type="string", help="directorio ficheros conf (php.ini,apache.con,default.conf)")
parser.add_option("-v", "--ver-apache", dest="verisonApache",default="5.6.30-apache", type="string",help="version de apache de docker-hub")
parser.add_option("-r", "--repositorio", dest="repositorio",default="hamal.unizar.es:5000", type="string",help="repository")

parser.add_option("-x", "--puerto-publico", dest="pext",default="noport", type="string",help="puerto exterior")
(options, args) = parser.parse_args()
print options
print args


username = options.username
name = options.dominio
password=options.passwd
versionApache=options.verisonApache
dirconf=options.dirconf
pext=options.pext
repositorio=options.repositorio
if username=="nouser":
	print "Obligado usuario"
	exit()
if name == "nouser":
	print "Obligado dominio"
	exit()
if password=="nopasswd":
	password=random_password()+"."
if pext == "noport":
        print "Obligado puerto exterior"
        exit()


try:
    uid=pwd.getpwnam(username).pw_uid
    print "Error 001 :el usuario "+username+" ya existe"
    
except KeyError:
    uid=n()
    createUser(name,username,password,str(uid))


ddir="storage/webs/"+name
if path.exists(ddir):
   print "Error 002 :el  path "+ddir+" ya existe"

print username
print name
print password
print ddir
print uid
print versionApache
print dirconf
print repositorio
#createUser(name,username,password)
createUser(name,username,password,str(uid))
imagen=cretaeImage(versionApache,repositorio,name,uid,dirconf)
print imagen
dir_conf_p=ddir+"/conf"
image=buildImagei2(imagen,name,dir_conf_p)
runImage(image,name,pext)

#deployStack(name,imagen,pext)
