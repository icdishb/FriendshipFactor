# A python implementation of ALIGNF
# Author: Huibin Shen
# 20.03.2015

import numpy as np
from  scipy.sparse import isspmatrix_csr

import mosek

def f_dot(X,Y):
    if isspmatrix_csr(X):
        t = X*Y
        return sum(t.data)
    else:
        return sum(sum(X*Y))

def center(km):
    """Center km if km is dense matrix"""
    if isspmatrix_csr(km):
        print "Centering a sparse matrix!!! Break the sparsity."
    m = len(km)
    I = np.eye(m)
    one = np.ones((m,1))
    t = I - np.dot(one,one.T)/m
    return np.dot(np.dot(t,km),t)

def streamprinter(text):
    sys.stdout.write(text)
    sys.stdout.flush()

def ALIGNF(km_list, ky, centering=True):
    """
    Parameters:
    -----------
    km_list, a list of kernel matrices, list of 2d array 
    ky, target kernel,  2d array

    Returns:
    --------
    xx, the weight for each kernels
    """
    n_feat = len(km_list)
    km_list_copy = []

    # center the kernel first
    for i in range(n_feat):
        if centering:
            km_list_copy.append(center(km_list[i].copy()))
        else:
            km_list_copy.append(km_list[i].copy())
    if centering:
        ky_copy = center(ky.copy())
    else:
        ky_copy = ky.copy()

    a = np.zeros(n_feat)
    for i in range(n_feat):
        a[i] = f_dot(km_list_copy[i], ky_copy)

    M = np.zeros((n_feat, n_feat))
    for i in range(n_feat):
        for j in range(i,n_feat):
            M[i,j] = f_dot(km_list_copy[i],km_list_copy[j])
            M[j,i] = M[i,j]

    Q = 2*M
    C = -2*a

    Q = Q + np.diag(np.ones(n_feat)*1e-10)

    ################################################
    # Using mosek to solve the quadratice programming

    # Set upper diagonal element to zeros, mosek only accept lower triangle
    iu = np.triu_indices(n_feat,1)
    Q[iu] = 0

    # start solving with mosek
    inf = 0.0
    env = mosek.Env()
    env.set_Stream(mosek.streamtype.log, streamprinter)

    # Create a task                                                     
    task = env.Task()
    task.set_Stream(mosek.streamtype.log, streamprinter)

    # Set up bound for variables                                  
    bkx = [mosek.boundkey.lo]* n_feat
    blx = [0.0] * n_feat
    bux = [+inf]* n_feat

    numvar = len(bkx)

    task.appendvars(numvar)

    for j in range(numvar):
        task.putcj(j,C[j])
        task.putvarbound(j,bkx[j],blx[j],bux[j])

    # Set up quadratic objective                                         
    inds = np.nonzero(Q)
    qsubi = inds[0].tolist()
    qsubj = inds[1].tolist()
    qval = Q[inds].tolist()

    # Input quadratic objective                                         
    task.putqobj(qsubi,qsubj,qval)

    # Input objective sense (minimize/mximize)                          
    task.putobjsense(mosek.objsense.minimize)

    task.optimize()

    # Print a summary containing information                            
    # about the solution for debugging purposes                         
    task.solutionsummary(mosek.streamtype.msg)

    solsta = task.getsolsta(mosek.soltype.itr)
    if (solsta == mosek.solsta.optimal or
        solsta == mosek.solsta.near_optimal):
        # Output a solution                                              
        xx = np.zeros(numvar, float)
        task.getxx(mosek.soltype.itr, xx)
        #xx = xx/np.linalg.norm(xx)
        return xx
    else:
        print "Solution not optimal or near optimal"
        print solsta
        return None


# test 
#km_list = []
#for i in range(5):
#    A = np.random.rand(5,5)
#    km_list.append(np.dot(A.T,A))

#B = np.random.rand(5,5)
#ky = np.dot(B.T,B)

#w = ALIGNF(km_list, ky)
#print w
