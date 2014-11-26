#!/usr/bin/env python
######################################################
## GUI to vizualize ROMS input/output files
## Nov 2014
## rsoutelino@gmail.com
######################################################
import os
import wx
import datetime as dt

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as Navbar
from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib.figure import Figure

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path
import scipy.io as sp
import netCDF4 as nc

from lib import *

# TO-DO LIST: ====================================================
#   - start
# ================================================================

# NICE TIP TO DEBUG THIS PROGRAM: ================================
#   - comment out app.MainLoop at the last line of this script
#   - ipython --gui=wx
#   - run pyromsgui.py
#   - trigger the events and check out the objects in the shell
# ================================================================


global currentDirectory
currentDirectory = os.getcwd()

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
DEFAULT_VMIN = 0 
DEFAULT_VMAX = 1.5 
DEFAULT_CMAP = plt.cm.BrBG
DEFAULT_DEPTH_FOR_LAND = -50


class App(wx.App):
    def OnInit(self):
        self.frame = Interface("PyRomsGUI 0.1.0", size=(1024,800))
        self.frame.Show()
        return True


class Interface(wx.Frame):
    def __init__(self, title=wx.EmptyString, pos=wx.DefaultPosition, 
                       size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE,
                       *args, **kwargs):
        wx.Frame.__init__(self, None, -1, "PyRomsGUI 0.1.0", pos=pos, 
                          size=size, style=style, *args, **kwargs)
        
        # Initializing toolbar
        self.toolbar = MainToolBar(self)


        # BASIC LAYOUT OF THE NESTED SIZERS ======================
        panel1 = wx.Panel(self, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        mplpanel = wx.Panel(self, wx.ID_ANY, style=wx.SUNKEN_BORDER)
        mplpanel.SetBackgroundColour("WHITE")

        # BOX 1 is the main sizer
        box1 = wx.BoxSizer(wx.HORIZONTAL)
        box1.Add(panel1, 1, wx.EXPAND)
        box1.Add(mplpanel, 4, wx.EXPAND)

        # BOX 2 is the inner sizer of the left big control panel
        box2 = wx.BoxSizer(wx.VERTICAL)

        # BOX 3 is the sizer of the right big parent panel(panel1), the one that will
        #    serve as base for two child panels which will hold
        #    the two matplotlib canvas's
        box3 = wx.BoxSizer(wx.VERTICAL)

        # panel 1 content ========================================
        variable = wx.StaticText(panel1, label="Variable")
        box2.Add(variable, proportion=0, flag=wx.CENTER)
        self.var_select = wx.ComboBox(panel1, value='Choose variable')
        box2.Add(self.var_select, proportion=0, flag=wx.CENTER)
        self.var_select.Bind(wx.EVT_COMBOBOX, self.toolbar.OnUpdateHslice)

        time = wx.StaticText(panel1, label="Time record")
        box2.Add(time, proportion=0, flag=wx.CENTER)
        self.time_select = wx.ComboBox(panel1, value='Choose time step')
        box2.Add(self.time_select, proportion=0, flag=wx.CENTER)
        self.time_select.Bind(wx.EVT_COMBOBOX, self.toolbar.OnUpdateHslice)

        # mplpanel content ========================================
        self.mplpanel = SimpleMPLCanvas(mplpanel)
        box3.Add(self.mplpanel.canvas, 1, flag=wx.CENTER) 

        # FINAL LAYOUT CONFIGURATIONS ============================
        self.SetAutoLayout(True)
        panel1.SetSizer(box2)
        # panel2.SetSizer(box4)
        mplpanel.SetSizer(box3)

        self.SetSizer(box1)

        self.InitMenu()
        self.Layout()
        self.Centre()
        # self.ShowModal()


    def InitMenu(self):
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        fileMenu.Append(wx.ID_OPEN, u'&Open ROMS grid file')
        fileMenu.Append(wx.ID_OPEN, u'&Open coastline file')
        fileMenu.Append(wx.ID_SAVE, '&Save grid')
        fileMenu.AppendSeparator()

        qmi = wx.MenuItem(fileMenu, wx.ID_EXIT, '&Quit\tCtrl+W')
        opf = wx.MenuItem(fileMenu, wx.ID_OPEN, '&Open\tCtrl+O')
        opc = wx.MenuItem(fileMenu, wx.ID_OPEN, '&Open\tCtrl+O+C')
        svf = wx.MenuItem(fileMenu, wx.ID_SAVE, '&Save\tCtrl+S')
        fileMenu.AppendItem(qmi)
        # fileMenu.AppendItem(svf)

        self.Bind(wx.EVT_MENU, self.OnQuit, qmi)
        self.Bind(wx.EVT_MENU, self.toolbar.OnLoadFile, opf)
        self.Bind(wx.EVT_MENU, self.toolbar.OnLoadCoastline, opc)
        self.Bind(wx.EVT_MENU, self.toolbar.OnPlotVslice, svf)

        menubar.Append(fileMenu, u'&PyRomsGUI')
        self.SetMenuBar(menubar)


    def OnQuit(self, e):
        """Fecha o programa"""
        self.Close()
        self.Destroy()


    def OnCloseWindow(self, e):
        self.Destroy()


class SimpleMPLCanvas(object):
    """docstring for SimpleMPLCanvas"""
    def __init__(self, parent):
        super(SimpleMPLCanvas, self).__init__()
        self.parent = parent
        self.plot_properties()
        self.make_navbar()
        
    def make_navbar(self):
        self.navbar = Navbar(self.canvas)   
        self.navbar.SetPosition(wx.Point(0,0)) # this is not working !!


    def plot_properties(self):
        # Create matplotlib figure
        self.fig = Figure(facecolor='w', figsize=(12,8))
        self.canvas = FigureCanvas(self.parent, -1, self.fig)
        
        self.ax   = self.fig.add_subplot(111)
        # tit = self.ax1.set_title("ROMS mask_rho", fontsize=12, fontweight='bold')
        # tit.set_position([0.9, 1.05])


class MainToolBar(object):
    def __init__(self, parent):
        self.currentDirectory = os.getcwd()
        self.parent = parent
        self.toolbar = parent.CreateToolBar(style=1, winid=1,
                                            name="Toolbar")
        self.tools_params ={ 
            'load_file': (load_bitmap('grid.png'), u"Load ROMS netcdf file",
                        "Load ocean_???.nc ROMS netcdf file"),
            'load_coastline': (load_bitmap('coast.png'), u"Load coastline",
                        "Load *.mat coastline file [lon / lat poligons]"),
            'plot_vslice': (load_bitmap('save.png'), u"Plot vertical slice",
                        "Plot vertical slice of some variable"),
            'settings': (load_bitmap('settings.png'), u"PyRomsGUI settings",
                        "PyRomsGUI configurations"),
            'quit': (load_bitmap('exit.png'), u"Quit",
                        "Quit PyRomsGUI"),
        }
        
        self.createTool(self.toolbar, self.tools_params['load_file'], 
                        self.OnLoadFile)
        self.createTool(self.toolbar, self.tools_params['load_coastline'], 
                        self.OnLoadCoastline)

        self.toolbar.AddSeparator()

        self.plot_vslice = self.createTool(self.toolbar, 
                                           self.tools_params['plot_vslice'], 
                                           self.OnPlotVslice, isToggle=True)

        self.toolbar.AddSeparator()

        self.createTool(self.toolbar, self.tools_params['settings'], 
                        self.OnSettings)
        self.createTool(self.toolbar, self.tools_params['quit'], 
                        self.parent.OnQuit)

        self.toolbar.Realize()


    def createTool(self, parent, params, evt, isToggle=False):
        tool = parent.AddTool(wx.NewId(), bitmap=params[0], shortHelpString=params[1],
                    longHelpString=params[2], isToggle=isToggle)
        self.parent.Bind(wx.EVT_TOOL, evt, id=tool.GetId())
        return tool


    def OnLoadFile(self, evt):
        openFileDialog = wx.FileDialog(self.parent, "Open roms netcdf file [*.nc]",
                                       "/ops/forecast/roms/", " ",
                                       "netcdf files (*.nc)|*.nc",
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if openFileDialog.ShowModal() == wx.ID_CANCEL:
            return     # the user changed idea...

        filename = openFileDialog.GetPath()
        self.ncfile = nc.Dataset(filename)

        # this function is intended to return relevant information on the file
        varlist, axeslist, time = taste_ncfile(self.ncfile)

        timelist = romsTime2string(time)
        app.frame.var_select.SetItems(varlist)
        app.frame.time_select.SetItems(timelist)
        app.frame.time_select.SetValue(timelist[0])

        # opening ROMS grid
        openFileDialog = wx.FileDialog(self.parent, "Open roms GRID netcdf file [*_grd.nc]",
                                       "/ops/forecast/roms/", " ",
                                       "netcdf files (*.nc)|*.nc",
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if openFileDialog.ShowModal() == wx.ID_CANCEL:
            return     # the user changed idea...

        grdname = openFileDialog.GetPath()
        self.grd = nc.Dataset(grdname)

        lon = self.grd.variables['lon_rho'][:]
        lat = self.grd.variables['lat_rho'][:]
        h   = self.grd.variables['h'][:]

        mplpanel = app.frame.mplpanel
        ax = mplpanel.ax
        self.pcolor = ax.pcolormesh(lon, lat, h)
        ax.set_xlim([lon.min(), lon.max()])
        ax.set_ylim([lat.min(), lat.max()])
        ax.set_aspect('equal')

        mplpanel.canvas.draw()


    def OnUpdateHslice(self, evt):
        varname = app.frame.var_select.GetValue()
        var = self.ncfile.variables[varname]
        dimensions = var.dimensions
        grid = dimensions[-1].split('_')[-1]
        lon = self.grd.variables['lon_'+grid][:]
        lat = self.grd.variables['lat_'+grid][:]

        # time index
        varlist, axeslist, time = taste_ncfile(self.ncfile)
        timestr = app.frame.time_select.GetValue()
        selected_time = string2romsTime(timestr, self.ncfile)
        tindex = np.where( time[:] == selected_time )[0][0]

        if len(dimensions) == 3:
            arr = var[tindex,...]
        if len(dimensions) == 4:
            arr = var[tindex,-1,...]

        mplpanel = app.frame.mplpanel
        ax = mplpanel.ax
        ax.clear()
        ax.pcolormesh(lon, lat, arr)
        ax.set_xlim([lon.min(), lon.max()])
        ax.set_ylim([lat.min(), lat.max()])
        ax.set_title("%s   %s" %(varname, timestr))
        ax.set_aspect('equal')

        mplpanel.canvas.draw()


    def OnLoadCoastline(self, evt):
        openFileDialog = wx.FileDialog(self.parent, "Open coastline file - MATLAB Seagrid-like format",
                                       "/home/rsoutelino/metocean/projects/mermaid", " ",
                                       "MAT files (*.mat)|*.mat",
                                       wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if openFileDialog.ShowModal() == wx.ID_CANCEL:
            return     # the user changed idea...

        filename = openFileDialog.GetPath()
        coast = sp.loadmat(filename)
        lon, lat = coast['lon'], coast['lat']

        mplpanel = app.frame.mplpanel
        ax = mplpanel.ax
        ax.plot(lon, lat, 'k')

        try:
            ax.set_xlim([self.grd.lonr.min(), self.grd.lonr.max()])
            ax.set_ylim([self.grd.latr.min(), self.grd.latr.max()])
        except AttributeError: # just in case a grid was not loaded before
            ax.set_xlim([np.nanmin(lon), np.nanmax(lon)])
            ax.set_ylim([np.nanmin(lat), np.nanmax(lat)])
        
        ax.set_aspect('equal')
        mplpanel.canvas.draw()


    def OnPlotVslice(self, evt):
        mplpanel = app.frame.mplpanel

        if self.plot_vslice.IsToggled():
            self.cid = mplpanel.canvas.mpl_connect('button_press_event', self.vslice)
        else:
            mplpanel.canvas.mpl_disconnect(self.cid)


    def OnSettings(self, evt):
        pass


    def vslice(self, evt):
        if evt.inaxes != app.frame.mplpanel.ax: return
        mplpanel = app.frame.mplpanel
        ax = mplpanel.ax
        x, y = evt.xdata, evt.ydata
        button = evt.button
        p = ax.plot(x, y, 'wo')
        try:
            self.points.append(p)
            self.area.append( (x, y) )
        except AttributeError:
            self.points = [p]
            self.area = [ (x, y) ]

        if len(self.points) == 2:
            ax.plot([self.area[0][0], self.area[1][0]], 
                    [self.area[0][1], self.area[1][1]], 'k')

            p1, p2 = self.area[0], self.area[1]

            # assigning relevant variables
            varname = app.frame.var_select.GetValue()
            var = self.ncfile.variables[varname]
            dimensions = var.dimensions
            grid = dimensions[-1].split('_')[-1]
            lon = self.grd.variables['lon_'+grid][:]
            lat = self.grd.variables['lat_'+grid][:]

            ts = self.ncfile.variables['theta_s'][:]
            tb = self.ncfile.variables['theta_b'][:]
            hc = self.ncfile.variables['hc'][:]
            nlev = var.shape[1]
            sc = ( np.arange(1, nlev + 1) - nlev - 0.5 ) / nlev
            sigma = self.ncfile.variables['Cs_r'][:]

            dl = ( np.gradient(lon)[1].mean() + np.gradient(lat)[0].mean() ) / 2
            siz = int(np.sqrt( (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 ) / dl)
            xs = np.linspace(p1[0], p2[0], siz)
            ys = np.linspace(p1[1], p2[1], siz)

            # time index
            varlist, axeslist, time = taste_ncfile(self.ncfile)
            timestr = app.frame.time_select.GetValue()
            selected_time = string2romsTime(timestr, self.ncfile)
            tindex = np.where( time[:] == selected_time )[0][0]

            # getting nearest values
            hsec, zeta, vsec = [], [], []
            for ind in range(xs.size):
                line, col = near2d(lon, lat, xs[ind], ys[ind])
                vsec.append( var[tindex, :, line, col] )
                hsec.append( self.grd.variables['h'][line, col] )
                zeta.append( self.ncfile.variables['zeta'][tindex, line, col] )

            vsec = np.array(vsec).transpose()
            hsec, zeta = np.array(hsec), np.array(zeta)
            xs = xs.reshape(1, xs.size).repeat(nlev, axis=0)
            ys = ys.reshape(1, ys.size).repeat(nlev, axis=0)
            zsec = get_zlev(hsec, sigma,  5, sc, ssh=zeta, Vtransform=2)

            plt.figure()
            plt.pcolormesh(xs, zsec, vsec)
            plt.colorbar()
            plt.show()

        mplpanel.canvas.draw()


        # elif button == 3:
        #     grd = self.grd
        #     path = Path( self.area )
        #     a, b = grd.lonr.shape
        #     for i in range(a):
        #         for j in range(b):
        #             if path.contains_point( [grd.lonr[i, j], 
        #                                      grd.latr[i, j] ] ) == 1:
        #                 grd.maskr[i,j] = 0
        #                 grd.h[i,j] = grd.hmin

        #     ax.clear()
        #     self.pcolor = ax.pcolormesh(grd.lonr, grd.latr, grd.maskr, 
        #                            vmin=DEFAULT_VMIN, vmax=DEFAULT_VMAX, 
        #                            cmap=DEFAULT_CMAP)
        #     ax.plot(grd.lonr, grd.latr, 'k', alpha=0.2)
        #     ax.plot(grd.lonr.transpose(), grd.latr.transpose(), 'k', alpha=0.2)
        #     ax.set_xlim([grd.lonr.min(), grd.lonr.max()])
        #     ax.set_ylim([grd.latr.min(), grd.latr.max()])
        #     ax.set_aspect('equal')
        #     mplpanel.canvas.draw()
        #     del self.points, self.area



def taste_ncfile(ncfile):
    try:
        if "history" in ncfile.type:
            filetype = 'his'
        elif 'restart' in ncfile.type:
            filetype = 'rst'
    except AttributeError: 
        print "Not a standard ROMS file !"

    varlist  = ROMSVARS[filetype]['variables']
    axeslist = ROMSVARS[filetype]['axes']

    for axes in axeslist:
        if 'time' in axes:
            time = ncfile.variables[axes]
        else:
            pass

    return varlist, axeslist, time


def romsTime2string(nctime):
    """
    nctime  :  netCDF4 variable
    """
    timeunits = nctime.units
    units = timeunits.split(' ')[0]
    tstart = dt.datetime.strptime(timeunits.split(' ')[-2], "%Y-%m-%d")
    timelist = []
    for t in nctime[:]:
        if units == 'seconds':
            current = tstart + dt.timedelta(seconds=t)
        if units == 'days':
            current = tstart + dt.timedelta(seconds=t*86400)

        timelist.append(current.strftime("%Y-%m-%d  %H h"))

    return timelist 


def string2romsTime(timelist, ncfile):
    if not isinstance(timelist, list):
        timelist = [timelist]

    varlist, axeslist, time = taste_ncfile(ncfile)
    timeunits = time.units
    units = timeunits.split(' ')[0]
    tstart = dt.datetime.strptime(timeunits.split(' ')[-2], "%Y-%m-%d")

    romstime = []
    for timestr in timelist:
        dttime = dt.datetime.strptime(timestr, "%Y-%m-%d  %H h")    
        delta = dttime - tstart
        if units == 'seconds':
            current = delta.seconds
        if units == 'days':
            current = delta.days

        romstime.append(current)

    if len(romstime) == 1:
        return romstime[0]
    else:
        return romstime


def load_bitmap(filename, direc=None):
    """
    Load a bitmap file from the ./icons subdirectory. 
    The filename parameter should not
    contain any path information as this is determined automatically.

    Returns a wx.Bitmap object
    copied from matoplotlib resources
    """

    if not direc:
        basedir = os.path.join(PROJECT_DIR,'icons')
    else:
        basedir = os.path.join(PROJECT_DIR, direc)

    bmpFilename = os.path.normpath(os.path.join(basedir, filename))
    if not os.path.exists(bmpFilename):
        raise IOError('Could not find bitmap file "%s"; dying'%bmpFilename)

    bmp = wx.Bitmap(bmpFilename)
    return bmp


if __name__ == "__main__":
    app = App(False)
    # app.MainLoop()






















