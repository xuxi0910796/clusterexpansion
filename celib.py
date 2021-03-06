#!/usr/bin/env python
import sys,re,math,itertools,shutil,os,random,subprocess
import numpy as np
import matplotlib.pyplot as plt
from fractions import Fraction
from sklearn.model_selection import learning_curve
from sklearn.metrics import mean_squared_error


_author_='Xu Xi'

def listwrite(afile,alist):
    'write a two-dimension list to file' 
    for i in alist:
        for j in i:
            if isinstance(j, float):
                afile.write('%.6f ' %(j))
            elif isinstance(j, str):
                afile.write('%s ' %(j))
            else:
                raise TypeError(j)
        afile.write('\n')

def projection(vector, basis):
    'return the coefficients of a vector on a basis'
    return np.dot(np.linalg.inv(np.transpose(basis)), vector)

def translation(site, platvect, slatvect):
    'generate a list of sites according to translation symmetry'
    sites=[]
    a_project=[projection(slatvect[x],platvect)[0] for x in range(3)]
    b_project=[projection(slatvect[x],platvect)[1] for x in range(3)]
    c_project=[projection(slatvect[x],platvect)[2] for x in range(3)]
    for i in range(int(min(a_project))-2,int(max(a_project))+2,1):
        for j in range(int(min(b_project))-2,int(max(b_project))+2,1):
            for k in range(int(min(c_project))-2,int(max(c_project))+2,1):
                tsite=np.array(site)+platvect[0]*i+platvect[1]*j+platvect[2]*k
                project=projection(tsite,slatvect)
                if min(project)>=0 and max(project)<1:
                    tsite=list(tsite)
                    tsite.append('')
                    sites.append(tsite)
    return sites

def occupy(strfile,sublattice,atomlist):
    i=0
    for sites in sublattice:
        if len(sites)!=len(atomlist[i]):
            print(sites, atomlist[i])
            raise RuntimeError('The number of site (%s) do not equal that of atoms (%s)' %(len(sites),len(atomlist[i])))
        j=0
        for site in sites:
            site[3]=atomlist[i][j]
            j+=1
        listwrite(strfile,sites)
        i+=1

def occupysaj(strfile,sublattice,atomlist):
    for i in range(len(sublattice)):
        for j in range(len(sublattice[i])):
            sublattice[i][j].append(atomlist[i][j])
    listwrite(strfile,sublattice)

def initstr(latfile, superlattice):
    'generate a random occupied structure'
    lattice = np.loadtxt('str.in', usecols=(0,1,2))
    supercell = np.loadtxt('supercell.in')

    strfile = open('str.out','w')
    listwrite(strfile, lattice[:3,:])
    listwrite(strfile, supercell)
    latvect = lattice[3:6, :]
    pvolume = abs(np.linalg.det(latvect))
    svolume = abs(np.linalg.det(supercell))
    n = int(round(svolume/pvolume))
    
    isublattices=[]
    iatomlist=[]
    vsublattices=[]
    sublattice_atoms=[]
    sublattice_c=[]
    sitecount=[]
    vatomlist=[]
    for line in open('str.in', 'r'):
        if len(line.split()) == 4:
            g=re.findall(r'(\w+)=(\d+)/(\d+)',line.split()[3])
            site = list(map(float,line.split()[:3]))
            sites = translation(site, latvect, supercell)
            if g==[]:
                isublattices.append(sites)
                atoms=[line.split()[3]]*n
                iatomlist.append(atoms)
            else:
                site_atom=[]
                site_c=[]
                for i in range(len(g)):
                    site_atom.append(g[i][0])
                    site_c.append(Fraction(int(g[i][1]),int(g[i][2])))
                if sum(site_c)!=1:
                    raise RuntimeError('The occupy probabilities of one site must sum up to 1')
                    #atoms=[]
                    #for i in range(len(a)):
                    #		b=[a[i]]*int(n*c[i])
                    #		atoms+=b
                    #random.shuffle(atoms)
                    #if a in vatoms:
                    #	vatomlist[vatoms.index(a)]+=atoms
                    #	vsublattices[vatoms.index(a)]+=sites
                    #else:
                    #	vatoms.append(a)
                    #	vatomlist.append(atoms)
                    #	vsublattices.append(sites)
                if site_atom in sublattice_atoms:
                    sitecount[sublattice_atoms.index(site_atom)]+=1
                    vsublattices[sublattice_atoms.index(site_atom)]+=sites
                else:
                    sublattice_atoms.append(site_atom)
                    sublattice_c.append(site_c)
                    sitecount.append(1)
                    vsublattices.append(sites)
    for i in range(len(sublattice_atoms)):
        atoms=[]
        for j in range(len(sublattice_atoms[i])):
            b=[sublattice_atoms[i][j]]*int(n*sublattice_c[i][j]*sitecount[i])
            atoms+=b
        random.shuffle(atoms)
        vatomlist.append(atoms)

    #print(isublattices, iatomlist)
    #print(vsublattices, vatomlist)
    occupy(strfile,isublattices,iatomlist)
    occupy(strfile,vsublattices,vatomlist)
    strfile.close()
    return isublattices,iatomlist,vsublattices,vatomlist,sublattice_c,n

def ce_energy(ecifile,strfile):
    'get energy from cluster expansion by the ATAT code corrdump'
    return float(subprocess.check_output('corrdump -c -eci=%s -s=%s' %(ecifile,strfile),shell=True))

def mdenergy(mcstep):
    'calculate Madelung energy' 
    #os.chdir(str(mcstep))
    subprocess.check_output('runstruct_vasp -nr&&py_conv -f POSCAR -i vasp -o w2k', shell=True)
    os.rename('POSCAR.struct',str(mcstep)+'.struct')
    subprocess.check_output('py_initmad -f '+str(mcstep)+'.struct')
    cmd='calcmad '+str(mcstep)+'.inmad'+'|grep Energy|head -1|awk \'{print $3}\''
    subprocess.check_output(cmd, shell=True)
    os.chdir('../')
    return float(output)

def sort(dictionary,number):
    dictionary=sorted(dictionary.iteritems(),key=lambda d:d[0])
    ground_index=dictionary[0][1]
    ground_energy=dictionary[0][0]
    os.rename(str(ground_index),'0')
    print('#the energy of ground state:',ground_energy,'\n','#the number of inequal structures:',len(dictionary))
    if number!=0:
        dictionary=dictionary[:number]
    dictionary=dict(dictionary)
    dictionary[ground_energy]='0'
    return dictionary

def swap(alist):
    'swap the position of two randomly choosen elements from a list'
    import random
    while 1:
        l=len(alist)
        e1=random.randrange(l)
        e2=random.randrange(l)
        if alist[e1]!=alist[e2]:
            alist[e1],alist[e2]=alist[e2],alist[e1]
            return alist
            break

def enumer(alist):
    'generate all possible combinations of a list of two elements'
    atoms=list(set(alist))
    sites=itertools.combinations(range(len(alist)),alist.count(atoms[0]))
    #allist=[]
    for i in sites:
        alist=[atoms[1]]*len(alist)
        for j in i:
            alist[j]=atoms[0]
        yield alist

def enumer_test(alist):
    'generate all posible combinations of a list'
    elements=list(set(alist))
    element_num=[]
    length=len(alist)
    for i in elements:
        element_num.append(alist.count(elements[i]))
    for j in range(len(elements)-1):
        selected_sites=itertools.combinations(range(length),element_num[i])
	
	
def getbandgap():
    'return a dictionary whose keys are index and values are bandgaps'
    bandgap={}
    rootdir=os.getcwd()
    filelist=os.listdir(rootdir)
    for ifile in filelist:
        fullpath=os.path.join(rootdir,ifile)
        if os.path.isdir(fullpath):
            os.chdir(fullpath)
            if os.path.isfile('OUTCAR'):
                output = subprocess.check_output('pv_gap.py OUTCAR|tail -1|awk \'{print $3}\'', shell=True)
                bandgap[str(ifile)]=float(output)
            else:
                print('No OUTCAR in', str(fullpath))
    os.chdir(rootdir)
    return bandgap

def touch(filename,value):
    'write a file with a value for cluster expansion'
    with open(filename,'w') as f:
        f.write('%s' %(value))

def objective_correlation_functions(concentration,cluster_order):
    'generate the objective cluster correlation functions or read it from input file'
    obj_corr=[]
    for i in range(len(cluster_order)):
        obj_corr.append((2*concentration[0][0]-1)**cluster_order[i])
    if os.path.isfile('tcorr.out'):
        read_corr=[]
        for line in file('tcorr.out'):
            read_corr.append(float(line.split()[0]))
        for j in range(len(read_corr)):
            obj_corr[j]=read_corr[j]
    return obj_corr

def Boltzmann_factor(energy,temperature):
    if temperature == -1: #-1 stands for the infinity temperature case
        return 1
    elif temperature == 0:
        raise ValueError('The temperature is 0.')
    else:
        exponent=-(energy*1.161E4)/temperature
        if exponent <=-50:
            return 0
        else:
            return math.pow(math.e,exponent)


def calc_correlation_functions(weight,obj_corr,radius):
    'calculate correlation functions'
    output = subprocess.check_output('corrdump -c -l=lat.in -s=str.out')
    str_corr = map(float, output.split())
    correlations=[]
    if len(str_corr)!=len(obj_corr):
        raise RuntimeError('The number of clusters whose correlation functions to be calculated do not match')
    else:
        for i in range(len(obj_corr)):
            correlations.append(str_corr[i]-obj_corr[i])
    if correlations==[0.0]*len(correlations):
        objective='perfect' 
        return objective,correlations
    else:
        for i in range(len(correlations)):
            if correlations[:i+1]==(i+1)*[0.0] and correlations[i+1]!=0.0:
                index=i
    if 'index' in vars():
        objective=sum(map(abs,correlations))-weight*radius[index]
    else:
        objective=sum(map(abs,correlations))
    return objective, correlations

def skipchoice(alist,number):
    import random
    while 1:
        selected=random.sample(alist,number)
        j=0
        for i in selected:
            if i+1 not in selected and i-1 not in selected:
                j+=1
        if j==len(selected):
            return selected
            break

def read_clusters(order):
    subprocess.check_call('getclus > clusters.tmp',shell=True)
    clus_data=list(np.loadtxt('clusters.tmp')[:,0])
    os.remove('clusters.tmp')
    exclude_clus_num=0
    for i in range(order):
        exclude_clus_num+=clus_data.count(i)
    return clus_data.count(order),exclude_clus_num

def read_cluster_number():
    'return a list whose elements are the number of clusters of increasing orders'
    subprocess.check_call('getclus > clusters.tmp',shell=True)
    clus_data=list(np.loadtxt('clusters.tmp')[:,0])
    os.remove('clusters.tmp')
    clus_order=set(map(int,clus_data))
    clus_number=[]
    for i in clus_order:
        clus_number.append(clus_data.count(i))
    return clus_number

def bandgap_temp(temperature,eci):
    mcdata=np.loadtxt('mc.out')
    noc=len(eci) #number of clusters
    mc_temps=map(round,list(mcdata[:,0])) #temperatures of MC simulation
    clus_corr_funcs=mcdata[:,-noc:] #cluster correlation functions
    #print(clus_corr_funcs)
    bandgap=list(np.dot(clus_corr_funcs,eci))
    return bandgap[mc_temps.index(temperature)]

def calc_cv(cluster_function,eci,real_values):
    'per site'
    #m = len(file('lat.in').readlines())-6 
    cv = 0

    #remove linear dependent columns of the matrix of cluster functions
    #a, inds = sympy.Matrix(cluster_function).rref()
    #cluster_function = cluster_function[:,inds]
    #eci = eci[inds]
    #print len(eci) 

    G = np.dot(np.transpose(cluster_function),cluster_function) #Gramian matrix
    #x = np.linalg.inv(G)
    #x = scipy.linalg.pinv(G)
    x = np.linalg.pinv(G,rcond=1e-15)
    predicted_values = np.dot(cluster_function,eci)
    n = len(cluster_function)
    for i in range(n):
        cv += (((real_values[i]-predicted_values[i])/(1-np.dot(np.dot(cluster_function[i,:],x),np.transpose(cluster_function[i,:]))))**2)
    #return math.sqrt(cv/n)/m
    return round(math.sqrt(cv/n),6)

def read_cluster_function():
    #return np.loadtxt('allcorr.out')
    cluster_function=[]
    subprocess.check_call('getclus > clusters.tmp',shell=True)
    clus_multi=np.loadtxt('clusters.tmp')[:,2]
    os.remove('clusters.tmp')
    for item in os.listdir(os.getcwd()):
        fullpath=os.path.join(os.getcwd(),item)
        if os.path.isdir(fullpath):
            #print fullpath
            os.chdir(fullpath)
            if os.path.isfile('str.out') and not os.path.isfile('error'):
                ccf = list(map(float, subprocess.check_output('corrdump -c -l=../lat.in -cf=../clusters.out', shell=True).split()))
                cluster_function.append(np.multiply(ccf, clus_multi))
            os.chdir('../')
    cluster_function=np.array(cluster_function,dtype='float')
    condition_number=np.linalg.cond(cluster_function)
    if condition_number >= 1E15:
        print("WARNING: The condition number of the matrix of cluster functions is too large: %.6e\n" %(np.linalg.cond(cluster_function)))
    return np.array(cluster_function)

def read_quantity(quantity,average=True):
    'quantity per lattice'
    quantities=[]
    n=len(file('lat.in').readlines())-6
    #m=int(subprocess.check_output('grep , lat.in | wc -l',shell=True))
    for item in os.listdir(os.getcwd()):
        fullpath = os.path.join(os.getcwd(),item)
        if os.path.isdir(fullpath):
            os.chdir(fullpath)
            if os.path.isfile(quantity) and not os.path.isfile('error'):
                if average == True:
                    atom_number = len(file('str.out').readlines())-6
                    site_number = (atom_number/n)
                    quantities.append(float(subprocess.check_output('cat %s' %(quantity),shell=True))/site_number)
                else:
                    quantities.append(float(subprocess.check_output('cat %s' %(quantity),shell=True)))
            os.chdir('../')
    return np.array(quantities)


def data_io(data,average=False):
    'collect successfully finished results and output them to a data file (unit in per atom)'
    lat_atom_number=len(open('lat.in', 'r').readlines())-6
    datafile=open('%s.dat' %(data),'w')
    datafile.write('#index\tx\t%s-vasp\t%s-ce\n' % (data,data))
    for item in os.listdir(os.getcwd()):
        fullpath=os.path.join(os.getcwd(),item)
        if os.path.isdir(fullpath):
            os.chdir(fullpath)
            if os.path.isfile(data) and not os.path.isfile('error'):
                datafile.write(str(os.path.basename(fullpath))+'\t')
                sc_x = float(subprocess.check_output('corrdump -pc -l=../lat.in',shell=True).strip().split()[-2]) #need debug 
                sc_atom_number=len(open('str.out', 'r').readlines())-6
                ce_data=float(subprocess.check_output('corrdump -c -l=../lat.in -cf=../clusters.out -eci=../%s.eci' %(data),shell=True))/lat_atom_number
                if average==True:
                    vasp_data=float(subprocess.check_output('cat %s' %(data),shell=True))
                else:
                    vasp_data=float(subprocess.check_output('cat %s' %(data),shell=True))/sc_atom_number
                    #ce_data=(sc_atom_number/lat_atom_number)*float(subprocess.check_output('corrdump -c -l=../lat.in -cf=../clusters.out -eci=../%s.eci' %(data),shell=True))
                datafile.write('%.3f\t%.5f\t%.5f\n' %(sc_x,vasp_data,ce_data))
            os.chdir('../')
    datafile.close()


def plot_eci(eci,filename):
    'use matplotlib to plot eci'
    _, a=read_clusters(2) #exclude null and point clusters
    plt.bar(range(len(eci[a:])),eci[a:],color='C7')
    plt.axhline(y=0,linewidth=.5,color='k')
    plt.ylabel('ECI/eV')
    plt.xlabel('Index of clusters')
    plt.savefig('%s.png' %(filename))

def plot_fit(y1,y2,cv,error):

    plt.scatter(y1,y2)
    a=max(max(y1),max(y2))
    b=min(min(y1),min(y2))
    d=(a-b)*0.2

    x=np.linspace(b-d,a+d,100)
    plt.plot(x,x,linestyle='dashed',linewidth=.5,c='k')

    plt.xlim(b-d,a+d)
    plt.ylim(b-d,a+d)

    plt.text(a-2*d,b,'CV = %.3f eV\nRMSD = %.3f eV' %(cv,error))

def plot_fit2(y1,y2):

    plt.scatter(y1,y2)
    a=max(max(y1),max(y2))
    b=min(min(y1),min(y2))
    d=(a-b)*0.2

    x=np.linspace(b-d,a+d,100)
    plt.plot(x,x,linestyle='dashed',linewidth=.5,c='k')

    plt.xlim(b-d,a+d)
    plt.ylim(b-d,a+d)

    rmsd = math.sqrt(mean_squared_error(y1,y2))
    plt.text(a-2*d,b,'RMSD = %.3f eV' %(rmsd))

def plot_learning_curve(estimator, X, y, ylim=None, cv=None,
                        n_jobs=1, train_sizes=[0.33, 0.55, 0.78, 1.]):
    'Generate a simple plot of the test and training learning curve.'

    train_sizes, train_scores, test_scores = learning_curve(estimator, X, y, cv=cv, scoring='neg_mean_squared_error',n_jobs=n_jobs, train_sizes=train_sizes)
    #train_sizes, train_scores, test_scores = learning_curve(estimator, X, y, cv=cv, scoring='neg_mean_absolute_error',n_jobs=n_jobs, train_sizes=train_sizes, shuffle=True, verbose=1)

    train_scores = [[math.sqrt(-x) for x in y] for y in train_scores]
    test_scores = [[math.sqrt(-x) for x in y] for y in test_scores]

    #print 'Train Score:\n',train_scores
    #print 'Test Score:\n',test_scores

    #train_scores_mean = map(lambda x: math.sqrt(x),-np.mean(train_scores, axis=1))
    train_scores_mean = np.mean(train_scores, axis=1)
    #train_scores_std = map(lambda x:math.sqrt(x),np.std(train_scores, axis=1))
    train_scores_std = np.std(train_scores, axis=1)
    #test_scores_mean = map(lambda x:math.sqrt(x),-np.mean(test_scores, axis=1))
    test_scores_mean = np.mean(test_scores, axis=1)
    #test_scores_std = map(lambda x:math.sqrt(x),np.std(test_scores, axis=1))
    test_scores_std = np.std(test_scores, axis=1)

    output = open('lc.dat','w')
    for i in range(len(train_sizes)):
        output.write('%i\t%.5f\t%.5f\t%.5f\t%.5f\n' %(train_sizes[i],train_scores_mean[i],train_scores_std[i],test_scores_mean[i],test_scores_std[i]))
    output.close()

    plt.figure()
    if ylim is not None:
        plt.ylim(*ylim)
    plt.xlabel("The Size of Training Set")
    plt.ylabel("RMSE/eV")
    plt.grid()
    plt.errorbar(train_sizes,train_scores_mean,yerr=train_scores_std,fmt='o--',color='C0',elinewidth=1,ecolor='C0',capsize=5,capthick=2,label='Training Score')
    plt.errorbar(train_sizes,test_scores_mean,yerr=test_scores_std,fmt='s--',color='C3',elinewidth=1,ecolor='C3',capsize=5,capthick=2,label='Test Score')
    plt.legend(loc="best")
    plt.show()

def BIC(cluster_function,ECI,y):
    'calculate the Bayesian Information Criterion of a linear model of cluster expansion'
    n,k = cluster_function.shape #the number of samples(structures) and parameters(clusters)
    MSE = mean_squared_error(y,np.dot(cluster_function,ECI))
    return n*math.log(MSE) + k*math.log(n)
