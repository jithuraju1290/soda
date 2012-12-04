# -*- coding: utf-8 -*-
"""
Tools for modifying suntans boundary condition files


Examples:
---------

Example 1) Modify the boundary condition markers with a shapefile:
------------------------------------------------------------------
    
    >>from sunboundary import modifyBCmarker
    >># Path to the grid
    >>suntanspath = 'C:/Projects/GOMGalveston/MODELLING/GRIDS/GalvestonCoarseBC'
    >># Name of the shapefile
    >>bcfile = '%s/Galveston_BndPoly.shp'%suntanspath 
    >>modifyBCmarker(suntanspath,bcfile)
    
Created on Fri Nov 02 15:24:12 2012

@author: mrayson
"""


import sunpy
import numpy as np
import matplotlib.pyplot as plt
from maptools import readShpPoly
import matplotlib.nxutils as nxutils #inpolygon equivalent lives here
from datetime import datetime, timedelta


class Boundary(object):
    """
    Generic SUNTANS boundary class
    
    Usage: 
        Boundary(suntanspath,timeinfo)
        
    Inputs:
        suntanspath - (string) 
        timeinfo - (3x1 tuple) (starttime,endtime,dt) where starttime/endtime
            have format 'yyyymmdd.HHMM' and dt in seconds
    """
    def __init__(self,suntanspath,timeinfo):
        
        self.suntanspath = suntanspath
        self.timeinfo = timeinfo
        
        self.grd = sunpy.Grid(suntanspath)
        
        self.loadBoundary()
        
        self.getTime()
        
        # Initialise the output arrays
        self.initArrays()
        
    def loadBoundary(self):
        """
        Load the coordinates and indices for type 2 and 3 BC's
        """
        ind2 = np.argwhere(self.grd.mark==2)
        ind3 = np.argwhere(self.grd.mark==3)
        
        # Edge index of type 2 boundaries
        self.edgep = ind2
        self.N2 = len(self.edgep)
        
        # Cell index of type 3 boundaries
        cellp1 = self.grd.grad[ind3,0]
        cellp2 = self.grd.grad[ind3,1]
        self.cellp=[]
        for c1,c2 in zip(cellp1,cellp2):
            if c1==-1:
                self.cellp.append(c2)
            elif c2==-1:
                self.cellp.append(c1)
        
        self.N3 = len(self.cellp)
        
        # Store the coordinates of the type 2 and 3 boundaries
        self.xv = self.grd.xv[self.cellp]
        self.yv = self.grd.yv[self.cellp]
        
        # Find the edge points
        xe = np.mean(self.grd.xp[self.grd.edges],axis=1)
        ye = np.mean(self.grd.yp[self.grd.edges],axis=1)
        self.xe = xe[self.edgep]
        self.ye = ye[self.edgep]
        
        # Get the depth info
        self.Nk = self.grd.Nkmax
        self.z = self.grd.z_r
    
    def getTime(self):
        """
        Load the timeinfo into a list of datetime objects
        """
        # build a list of timesteps
        t1 = datetime.strptime(self.timeinfo[0],'%Y%m%d.%H%M')
        t2 = datetime.strptime(self.timeinfo[1],'%Y%m%d.%H%M')
        
        self.time = []
        t0=t1
        while t0 < t2:
            self.time.append(t0)
            t0 += timedelta(seconds=self.timeinfo[2])
        
        self.Nt = len(self.time)
                
    def ncTime(self):
        """
        Return the time as seconds since 1990-01-01
        """        
        nctime = []
        for t in self.time:
            dt = t-datetime(1990,1,1)
            nctime.append(dt.total_seconds())
            
        return np.asarray(nctime)
        
    def initArrays(self):
        """
        Initialise the boundary condition arrays
        
        Type 3 variables are at the cell-centre (xv,yv) and are named:
            uv, vc, wc, h, T, S
            
            Dimensions: [Nt,Nk,N3]
            
        Type 2 variables are at the cell edges (xe, ye) and are named:
            boundary_u
            boundary_v
            boundary_w
            boundary_T
            boundary_S
            (no h)
            
            Dimensions: [Nt, Nk, N2]
        """
        
        # Type 2 arrays
        self.boundary_u = np.zeros((self.Nt,self.Nk,self.N2))
        self.boundary_v = np.zeros((self.Nt,self.Nk,self.N2))
        self.boundary_w = np.zeros((self.Nt,self.Nk,self.N2))
        self.boundary_T = np.zeros((self.Nt,self.Nk,self.N2))
        self.boundary_S = np.zeros((self.Nt,self.Nk,self.N2))
        
        # Type 3 arrays
        self.uc = np.zeros((self.Nt,self.Nk,self.N3))
        self.vc = np.zeros((self.Nt,self.Nk,self.N3))
        self.wc = np.zeros((self.Nt,self.Nk,self.N3))
        self.T = np.zeros((self.Nt,self.Nk,self.N3))
        self.S = np.zeros((self.Nt,self.Nk,self.N3))
        self.h = np.zeros((self.Nt,self.N3))
    
    def write2NC(self,ncfile):
        """
        Method for writing to the suntans boundary netcdf format
        
        """
        from netCDF4 import Dataset
        
        nc = Dataset(ncfile, 'w', format='NETCDF4_CLASSIC')
        
        # Define the dimensions
        nc.createDimension('Nt',None) # unlimited
        nc.createDimension('Nk',self.Nk)
        if self.N2>0:
            nc.createDimension('Ntype2',self.N2)
        if self.N3>0:    
            nc.createDimension('Ntype3',self.N3)
        
        
        ###
        # Define the coordinate variables and their attributes
        
        if self.N3>0:    
            # xv
            tmpvar=nc.createVariable('xv','f8',('Ntype3',))
            tmpvar[:] = self.xv
            tmpvar.setncattr('long_name','Easting of type-3 boundary points')
            tmpvar.setncattr('units','metres')
    
            # yv
            tmpvar=nc.createVariable('yv','f8',('Ntype3',))
            tmpvar[:] = self.yv
            tmpvar.setncattr('long_name','Northing of type-3 boundary points')
            tmpvar.setncattr('units','metres')
            
            # Type 3 indices
            tmpvar=nc.createVariable('cellp','i4',('Ntype3',))
            tmpvar[:] = self.cellp
            tmpvar.setncattr('long_name','Index of suntans grid cell corresponding to type-3 boundary')
            tmpvar.setncattr('units','')
        
        if self.N2>0:    
            # xe
            tmpvar=nc.createVariable('xe','f8',('Ntype2',))
            tmpvar[:] = self.xe
            tmpvar.setncattr('long_name','Easting of type-2 boundary points')
            tmpvar.setncattr('units','metres')
    
            # ye
            tmpvar=nc.createVariable('ye','f8',('Ntype2',))
            tmpvar[:] = self.ye
            tmpvar.setncattr('long_name','Northing of type-2 boundary points')
            tmpvar.setncattr('units','metres')
    
            # Type 2 indices
            tmpvar=nc.createVariable('edgep','i4',('Ntype2',))
            tmpvar[:] = self.edgep
            tmpvar.setncattr('long_name','Index of suntans grid edge corresponding to type-2 boundary')
            tmpvar.setncattr('units','')
        
        # z
        tmpvar=nc.createVariable('z','f8',('Nk',))
        tmpvar[:] = self.z
        tmpvar.setncattr('long_name','Vertical grid mid-layer depth')
        tmpvar.setncattr('units','metres')
        
        # time
        tmpvar=nc.createVariable('time','f8',('Nt',))
        tmpvar[:] = self.ncTime()
        tmpvar.setncattr('long_name','Boundary time')
        tmpvar.setncattr('units','')
        
        ###
        # Define the boundary data variables and their attributes
        
        ###
        # Type-2 boundaries
        if self.N2>0:    
            tmpvar=nc.createVariable('boundary_u','f8',('Nt','Nk','Ntype2'))
            tmpvar[:] = self.boundary_u
            tmpvar.setncattr('long_name','Eastward velocity at type-2 boundary point')
            tmpvar.setncattr('units','metre second-1')
                    
            tmpvar=nc.createVariable('boundary_v','f8',('Nt','Nk','Ntype2'))
            tmpvar[:] = self.boundary_v
            tmpvar.setncattr('long_name','Northward velocity at type-2 boundary point')
            tmpvar.setncattr('units','metre second-1')
                    
            tmpvar=nc.createVariable('boundary_w','f8',('Nt','Nk','Ntype2'))
            tmpvar[:] = self.boundary_w
            tmpvar.setncattr('long_name','Vertical velocity at type-2 boundary point')
            tmpvar.setncattr('units','metre second-1')
    
            tmpvar=nc.createVariable('boundary_T','f8',('Nt','Nk','Ntype2'))
            tmpvar[:] = self.boundary_T
            tmpvar.setncattr('long_name','Water temperature at type-2 boundary point')
            tmpvar.setncattr('units','degrees C')
    
            tmpvar=nc.createVariable('boundary_S','f8',('Nt','Nk','Ntype2'))
            tmpvar[:] = self.boundary_S
            tmpvar.setncattr('long_name','Salinity at type-2 boundary point')
            tmpvar.setncattr('units','psu')
        
        ###
        # Type-3 boundaries
        if self.N3>0:
            tmpvar=nc.createVariable('uc','f8',('Nt','Nk','Ntype3'))
            tmpvar[:] = self.uc
            tmpvar.setncattr('long_name','Eastward velocity at type-3 boundary point')
            tmpvar.setncattr('units','metre second-1')
                    
            tmpvar=nc.createVariable('vc','f8',('Nt','Nk','Ntype3'))
            tmpvar[:] = self.vc
            tmpvar.setncattr('long_name','Northward velocity at type-3 boundary point')
            tmpvar.setncattr('units','metre second-1')
                    
            tmpvar=nc.createVariable('wc','f8',('Nt','Nk','Ntype3'))
            tmpvar[:] = self.wc
            tmpvar.setncattr('long_name','Vertical velocity at type-3 boundary point')
            tmpvar.setncattr('units','metre second-1')
    
            tmpvar=nc.createVariable('T','f8',('Nt','Nk','Ntype3'))
            tmpvar[:] = self.T
            tmpvar.setncattr('long_name','Water temperature at type-3 boundary point')
            tmpvar.setncattr('units','degrees C')
    
            tmpvar=nc.createVariable('S','f8',('Nt','Nk','Ntype3'))
            tmpvar[:] = self.T
            tmpvar.setncattr('long_name','Salinity at type-3 boundary point')
            tmpvar.setncattr('units','psu')
            
            tmpvar=nc.createVariable('h','f8',('Nt','Ntype3'))
            tmpvar[:] = self.h
            tmpvar.setncattr('long_name','Water surface elevation at type-3 boundary point')
            tmpvar.setncattr('units','metres')
        
        nc.close()
        
        print 'Boundary data sucessfully written to: %s'%ncfile
        
        
def modifyBCmarker(suntanspath,bcfile):
    """
    Modifies SUNTANS boundary markers with a shapefile

    The shapefile must contain polygons with the integer-type field "marker"
    """
    
    print '#######################################################'
    print '     Modifying the boundary markers for grid in folder:'
    print '         %s'%suntanspath

    # Load the grid into an object
    grd = sunpy.Grid(suntanspath)
    
    # Find the edge points
    xe = np.mean(grd.xp[grd.edges],axis=1)
    ye = np.mean(grd.yp[grd.edges],axis=1)
    
    # Read the shapefile
    XY,newmarker = readShpPoly(bcfile,FIELDNAME='marker')
    if len(XY)<1:
        print 'Error - could not find any polygons with the field name "marker" in shapefile: %s'%bcfile
        return
    
    # Plot before updates
    #plt.figure()
    #grd.plotBC()
    #plt.plot(XY[0][:,0],XY[0][:,1],'m',linewidth=2)
    #plt.show()
    
    # Find the points inside each of the polygon and assign new bc
    for xpoly, bctype in zip(XY,newmarker):
        ind0 = grd.mark>0
        edges = np.asarray([xe[ind0],ye[ind0]])
        mark = grd.mark[ind0]
        ind1 = nxutils.points_inside_poly(edges.T,xpoly)
        mark[ind1]=bctype
        grd.mark[ind0]=mark
    
    # Save the new markers to edges.dat
    edgefile = suntanspath+'/edges.dat'
    grd.saveEdges(edgefile)
    print 'Updated markers written to: %s'%(edgefile)
    
    # Plot the markers
    plt.figure()
    grd.plotBC()
    plt.plot(XY[0][:,0],XY[0][:,1],'m',linewidth=2)
    figfile = suntanspath+'/BoundaryMarkerTypes.pdf'
    plt.savefig(figfile)
    
    print 'Marker plot saved to: %s'%(figfile)
    print 'Done.'
    print '#######################################################'
    

###################
# Testing stuff