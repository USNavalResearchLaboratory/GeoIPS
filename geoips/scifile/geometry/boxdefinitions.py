# pyresample, Resampling of remote sensing image data in python
#
# Copyright (C) 2010-2015
#
# Authors:
#    Esben S. Nielsen
#    Thomas Lavergne
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.

# Modified by Naval Research Laboratory, Marine Meteorology Division
# to allow non-swath definitions.

# 20160126 MLS  Copied pyresample/geometry.py to scifile/geometry/boxdefinitions.py
#                   Added false corners to SwathDefinition (may want to create a 
#                   new one anyway, since SwathDefinition supports 1D swaths, and 
#                   false corners may not work with 1D)
#               May add PlanarDefinition in future (simple min/max lat/lon boxes)
#                   This may be Step 4?
#               Pull all the pyresample/spherical_geometry.py calls out and use
#                   scifile/geometry/spherical.py instead (that will be step 2)
# 20160405 MLS  In Class Line intersection method - for self vertical or other vertical,
#                   previously had only checked that point lats fell within line segment,
#                   Need to also check point lons (otherwise other side of world would
#                   match).
#               Initially when I made this fix, large boxes started failing. Unrelated - 
#                   in planar_point_inside (which was called from 
#                   PlanarPolygonDefinition->overlaps_minmax_latlon->overlaps->__contains__/in)
#                   point prints degrees for str, but point.lon and point.lat are stored as radians.
#                   minlon/maxlon also radians. Was comparing math.degrees(point.lon) to minlon/maxlon
#                   This is why big sectors were failing, after fixing the
#                   "other side of the world" problem.
# 20160406 MLS  BaseDefinition.intersection was failing if all the corners of the 
#                   area_definition fell inside the data box definition.
#                   I think __contains__ in spherical_geometry is
#                   not working properly?  If intersection_polygon doesn't return
#                   anything, check that each corner of self is in other (then return 
#                   self.corners), then check that each corner of other is in self
#                   (return other.corners).
#                   This DOES NOT WORK for over the pole... Still need to handle that case.
# 20160407 MLS  Man this was buggy.  Need to do planar_point_inside instead of just 'in' (__contains__)
#                   for PlanarPolygonDefinition.overlaps.
#                   Previously just did if i in other or if i in self.
#                   This does not take 2d_false_corners into account
#                   when doing i in *area_definition* (other) because it uses
#                   area_definition.__contains__, which does not use
#                   planar_point_inside, but spherical point_inside.
#                   which fails for non-great circle-bounded data.
# 20161205 MLS  Forced sectoring to work for ahi...
#    driver: took out of hard coded list of things to not sector, print out original data shape and sectored data shape (watch for errors, in case something isn't defined..)
#    Overpass: add clat/clon to opass object
#    pass_prediction: create curr_opass directly from info, instead of hard coding the "focuspasses" string and passing to from_focuspasses.
#                        watch for start_dt / end_dt (hard coded passing base_dt - est_time/2 and base_dt + est_time/2 - do we always want base_dt to be the center time ?
#    containers: LAME if +- 0.1 doesn't return a corner, try +- 5. Shouldn't break anything (since it tries +- 0.1 first), but very lame...
#    boxdefinitions.py: actually finished PlanarPolygonDefinition
#                FIXED Line intersection - abs when checking difference against EPSILON....
#                                          Coordinate actually takes degrees, not radians
#                                          HOW WAS THIS EVER WORKING ?!  Did we actually use this at all...? I thought we did for quick coverage check...
#                FINISHED planar_intersection_polygon - Apparently this was barely even started...
#                            basically first checks if any points are completely contained within the other polygon - if so they get to be intersect corners
#                            next creates lines between each point of each shape (oops, right now only 4 corners, should be able to easily extend to arbitrary number...)
#                            loop through each point on the first shape against all the points in the other shape,
#                                check intersection (using recently corrected Line intersection mentioned above)
#                            return list of 4 Coordinates determined above (again, easily extend to more than 4...)

"""Classes for geometry operations"""

from __future__ import absolute_import

# Python Standard Libraries
import warnings
import math
import logging

# Installed Libraries
import numpy as np
from pyproj import Geod
from pyresample import utils
from pyresample import _spatial_mp
from IPython import embed as shell

log = logging.getLogger(__name__)

EPSILON = 0.0000001


class DimensionError(Exception):
    pass


class Boundary(object):

    """Container for geometry boundary.
    Labelling starts in upper left corner and proceeds clockwise"""

    def __init__(self, side1, side2, side3, side4):
        self.side1 = side1
        self.side2 = side2
        self.side3 = side3
        self.side4 = side4


class BaseDefinition(object):

    """Base class for geometry definitions"""

    def __init__(self, lons=None, lats=None, nprocs=1):
        if type(lons) != type(lats):
            raise TypeError('lons and lats must be of same type')
        elif lons is not None:
            if lons.shape != lats.shape:
                raise ValueError('lons and lats must have same shape')

        self.nprocs = nprocs

        # check the latitutes
        if lats is not None and ((lats.min() < -90. or lats.max() > +90.)):
            # throw exception
            raise ValueError(
                'Some latitudes are outside the [-90.;+90] validity range')
        else:
            self.lats = lats

        # check the longitudes
        if lons is not None and ((lons.min() < -180. or lons.max() >= +180.)):
            # issue warning
            warnings.warn('All geometry objects expect longitudes in the [-180:+180[ range. ' +
                          'We will now automatically wrap your longitudes into [-180:+180[, and continue. ' +
                          'To avoid this warning next time, use routine utils.wrap_longitudes().')
            # wrap longitudes to [-180;+180[
            self.lons = utils.wrap_longitudes(lons)
        else:
            self.lons = lons

        self.cartesian_coords = None

    def __eq__(self, other):
        """Test for approximate equality"""

        if other.lons is None or other.lats is None:
            other_lons, other_lats = other.get_lonlats()
        else:
            other_lons = other.lons
            other_lats = other.lats

        if self.lons is None or self.lats is None:
            self_lons, self_lats = self.get_lonlats()
        else:
            self_lons = self.lons
            self_lats = self.lats

        try:
            return (np.allclose(self_lons, other_lons, atol=1e-6,
                                rtol=5e-9) and
                    np.allclose(self_lats, other_lats, atol=1e-6,
                                rtol=5e-9))
        except (AttributeError, ValueError):
            return False

    def __ne__(self, other):
        """Test for approximate equality"""

        return not self.__eq__(other)

    def get_lonlat(self, row, col):
        """Retrieve lon and lat of single pixel

        :Parameters:
        row : int
        col : int

        :Returns:
        (lon, lat) : tuple of floats
        """

        if self.ndim != 2:
            raise DimensionError(('operation undefined '
                                  'for %sD geometry ') % self.ndim)
        elif self.lons is None or self.lats is None:
            raise ValueError('lon/lat values are not defined')
        return self.lons[row, col], self.lats[row, col]

    def get_lonlats(self, data_slice=None, **kwargs):
        """Base method for lon lat retrieval with slicing"""

        if self.lons is None or self.lats is None:
            raise ValueError('lon/lat values are not defined')
        elif data_slice is None:
            return self.lons, self.lats
        else:
            return self.lons[data_slice], self.lats[data_slice]

    def get_boundary_lonlats(self):
        """Returns Boundary objects"""

        side1 = self.get_lonlats(data_slice=(0, slice(None)))
        side2 = self.get_lonlats(data_slice=(slice(None), -1))
        side3 = self.get_lonlats(data_slice=(-1, slice(None)))
        side4 = self.get_lonlats(data_slice=(slice(None), 0))
        return Boundary(side1[0], side2[0], side3[0][::-1], side4[0][::-1]), Boundary(side1[1], side2[1], side3[1][::-1], side4[1][::-1])

    def get_cartesian_coords(self, nprocs=None, data_slice=None, cache=False):
        """Retrieve cartesian coordinates of geometry definition

        :Parameters:
        nprocs : int, optional
            Number of processor cores to be used.
            Defaults to the nprocs set when instantiating object
        data_slice : slice object, optional
            Calculate only cartesian coordnates for the defined slice
        cache : bool, optional
            Store result the result. Requires data_slice to be None

        :Returns:
        cartesian_coords : numpy array
        """

        if self.cartesian_coords is None:
            # Coordinates are not cached
            if nprocs is None:
                nprocs = self.nprocs

            if data_slice is None:
                # Use full slice
                data_slice = slice(None)

            lons, lats = self.get_lonlats(nprocs=nprocs, data_slice=data_slice)

            if nprocs > 1:
                cartesian = _spatial_mp.Cartesian_MP(nprocs)
            else:
                cartesian = _spatial_mp.Cartesian()

            cartesian_coords = cartesian.transform_lonlats(np.ravel(lons),
                                                           np.ravel(lats))

            if isinstance(lons, np.ndarray) and lons.ndim > 1:
                # Reshape to correct shape
                cartesian_coords = cartesian_coords.reshape(lons.shape[0],
                                                            lons.shape[1], 3)

            if cache and data_slice is None:
                self.cartesian_coords = cartesian_coords
        else:
            # Coordinates are cached
            if data_slice is None:
                cartesian_coords = self.cartesian_coords
            else:
                cartesian_coords = self.cartesian_coords[data_slice]

        return cartesian_coords

    @property
    def corners(self):
        """Returns the corners of the current area.
        """
        from pyresample.spherical_geometry import Coordinate
        return [Coordinate(*self.get_lonlat(0, 0)),
                Coordinate(*self.get_lonlat(0, -1)),
                Coordinate(*self.get_lonlat(-1, -1)),
                Coordinate(*self.get_lonlat(-1, 0))]

    def __contains__(self, point):
        """Is a point inside the 4 corners of the current area? This uses
        great circle arcs as area boundaries.
        """
        #### Original 
        from pyresample.spherical_geometry import point_inside, Coordinate
        corners = self.corners

        if isinstance(point, tuple):
            return point_inside(Coordinate(*point), corners)
        else:
            return point_inside(point, corners)
        #### End Original
        #from .spherical import SphPolygon
        #log.info('RUNNING SPHERICAL in __contains__')
        #sphpoly = SphPolygon(corners)
        #return sphpoly.intersection(SphPolygon(point), sphpoly)

    def overlaps(self, other):
        """Tests if the current area overlaps the *other* area. This is based
        solely on the corners of areas, assuming the boundaries to be great
        circles.

        :Parameters:
        other : object
            Instance of subclass of BaseDefinition

        :Returns:
        overlaps : bool
        """

        #from .spherical import Arc
        from pyresample.spherical_geometry import Arc

        self_corners = self.corners

        other_corners = other.corners

        for i in self_corners:
            if i in other:
                return True
        for i in other_corners:
            if i in self:
                return True

        self_arc1 = Arc(self_corners[0], self_corners[1])
        self_arc2 = Arc(self_corners[1], self_corners[2])
        self_arc3 = Arc(self_corners[2], self_corners[3])
        self_arc4 = Arc(self_corners[3], self_corners[0])

        other_arc1 = Arc(other_corners[0], other_corners[1])
        other_arc2 = Arc(other_corners[1], other_corners[2])
        other_arc3 = Arc(other_corners[2], other_corners[3])
        other_arc4 = Arc(other_corners[3], other_corners[0])

        for i in (self_arc1, self_arc2, self_arc3, self_arc4):
            for j in (other_arc1, other_arc2, other_arc3, other_arc4):
                if i.intersects(j):
                    return True
        return False

    def get_area(self):
        """Get the area of the convex area defined by the corners of the current
        area.
        """
        ### Original
        from pyresample.spherical_geometry import get_polygon_area

        return get_polygon_area(self.corners)
        ### End Original
        #from .spherical import SphPolygon
        #shell()
        #log.info('RUNNING SPHERICAL in get_area')

        #return SphPolygon(self.corners).area

    def intersection(self, other):
        """Returns the corners of the intersection polygon of the current area
        with *other*.

        :Parameters:
        other : object
            Instance of subclass of BaseDefinition

        :Returns:
        (corner1, corner2, corner3, corner4) : tuple of points
        """
        ### Original
        from pyresample.spherical_geometry import intersection_polygon
        # MLS This was failing if all the corners of the 
        #       area_definition fell inside the data box definition.
        #       I think __contains__ in spherical_geometry is
        #       not working properly?  This seems to work, should
        #       watch for false positives ?
        # This DOES NOT WORK for over the pole...
        allselfcornersin = False
        allothercornersin = False
        retcorners = intersection_polygon(self.corners, other.corners)
        if not retcorners:
            # Only try these if intersection_polygon didn't return anything.
            for i in self.corners:
                if planar_point_inside(i,other.corners):
                    allselfcornersin = True
                else:
                    allselfcornersin = False
            for i in other.corners:
                if planar_point_inside(i,self.corners):
                    allothercornersin = True
                else:
                    allothercornersin = False

            if allselfcornersin:
                return self.corners
            if allothercornersin:  
                return other.corners
        return retcorners
        
        ### End Original
        #from .spherical import SphPolygon
        #log.info('RUNNING SPHERICAL in intersection')
        #shell()
        #sphpoly = SphPolygon(self.corners)
        #return sphpoly.intersection(SphPolygon(other.corners))

    def overlap_rate(self, other):
        """Get how much the current area overlaps an *other* area.

        :Parameters:
        other : object
            Instance of subclass of BaseDefinition

        :Returns:
        overlap_rate : float
        """

        ### Original
        from pyresample.spherical_geometry import get_polygon_area
        other_area = other.get_area()
        inter_area = get_polygon_area(self.intersection(other))
        return inter_area / other_area
        ### End Original
        #from .spherical import SphPolygon
        #log.info('RUNNING SPHERICAL in overlap_rate')
        #selfpoly = SphPolygon(self.corners)
        #otherpoly = SphPolygon(other.corners)
        #other_area = other.get_area()
        #inter_area = selfpoly.intersection(otherpoly)
        #return inter_area / other_area


class CoordinateDefinition(BaseDefinition):

    """Base class for geometry definitions defined by lons and lats only"""

    def __init__(self, lons, lats, nprocs=1):
        if lons.shape == lats.shape and lons.dtype == lats.dtype:
            self.shape = lons.shape
            self.size = lons.size
            self.ndim = lons.ndim
            self.dtype = lons.dtype
        else:
            raise ValueError(('%s must be created with either '
                              'lon/lats of the same shape with same dtype') %
                             self.__class__.__name__)
        super(CoordinateDefinition, self).__init__(lons, lats, nprocs)

    def concatenate(self, other):
        if self.ndim != other.ndim:
            raise DimensionError(('Unable to concatenate %sD and %sD '
                                  'geometries') % (self.ndim, other.ndim))
        klass = _get_highest_level_class(self, other)
        lons = np.concatenate((self.lons, other.lons))
        lats = np.concatenate((self.lats, other.lats))
        nprocs = min(self.nprocs, other.nprocs)
        return klass(lons, lats, nprocs=nprocs)

    def append(self, other):
        if self.ndim != other.ndim:
            raise DimensionError(('Unable to append %sD and %sD '
                                  'geometries') % (self.ndim, other.ndim))
        self.lons = np.concatenate((self.lons, other.lons))
        self.lats = np.concatenate((self.lats, other.lats))
        self.shape = self.lons.shape
        self.size = self.lons.size

    def __str__(self):
        # Rely on numpy's object printing
        return ('Shape: %s\nLons: %s\nLats: %s') % (str(self.shape),
                                                    str(self.lons),
                                                    str(self.lats))


class GridDefinition(CoordinateDefinition):

    """Grid defined by lons and lats

    :Parameters:
    lons : numpy array
    lats : numpy array
    nprocs : int, optional
        Number of processor cores to be used for calculations.

    :Attributes:
    shape : tuple
        Grid shape as (rows, cols)
    size : int
        Number of elements in grid

    Properties:
    lons : object
        Grid lons
    lats : object
        Grid lats
    cartesian_coords : object
        Grid cartesian coordinates
    """

    def __init__(self, lons, lats, nprocs=1):
        if lons.shape != lats.shape:
            raise ValueError('lon and lat grid must have same shape')
        elif lons.ndim != 2:
            raise ValueError('2 dimensional lon lat grid expected')

        super(GridDefinition, self).__init__(lons, lats, nprocs)


class SwathDefinition(CoordinateDefinition):

    """Swath defined by lons and lats

    :Parameters:
    lons : numpy array
    lats : numpy array
    nprocs : int, optional
        Number of processor cores to be used for calculations.

    :Attributes:
    shape : tuple
        Swath shape
    size : int
        Number of elements in swath
    ndims : int
        Swath dimensions

    Properties:
    lons : object
        Swath lons
    lats : object
        Swath lats
    cartesian_coords : object
        Swath cartesian coordinates
    """

    def __init__(self, lons, lats, nprocs=1):
        if lons.shape != lats.shape:
            raise ValueError('lon and lat arrays must have same shape')
        elif lons.ndim > 2:
            raise ValueError('Only 1 and 2 dimensional swaths are allowed')
        super(SwathDefinition, self).__init__(lons, lats, nprocs)

    def overlaps_minmaxlatlon(self,other):
        """Tests if the current area overlaps the *other* area. This is based
        solely on the min/max lat/lon of areas, assuming the boundaries to be 
        along lat/lon lines.

        :Parameters:
        other : object
            Instance of subclass of BaseDefinition

        :Returns:
        overlaps : bool
        """
        self_corners = get_2d_false_corners(self)
        other_corners = get_2d_false_corners(other)
        log.info('    Swath 2d False Corners: '+str(self_corners))
        log.info('    Other 2d False Corners: '+str(other_corners))

        for i in self_corners:
            if planar_point_inside(i,other_corners):
                return True
        for i in other_corners:
            if planar_point_inside(i,self_corners):
                return True
        return False

    @property
    def corners(self):
        """Returns the corners of the current area.
        """
        try:
            # Try to just set normal CoordinateDefinition corners
            #    (Which doesn't work with bad vals in corners)
            return super(CoordinateDefinition, self).corners
        except ValueError:
            #print '        Corners failed on CoordinateDefinition, try falsecorners'
            pass

        lons, lats = self.get_lonlats()

        #Determine which rows and columns contain good data
        rows = lons.any(axis=1)
        cols = lons.any(axis=0)

        #Get the minimum and maximum row and column that contain good data
        good_row_inds = np.where(~rows.mask)[0]
        min_row = good_row_inds.min()
        max_row = good_row_inds.max()

        good_col_inds = np.where(~cols.mask)[0]
        min_col = good_col_inds.min()
        max_col = good_col_inds.max()

        log.info('    USING FALSE CORNERS!! setting corners. min row/col: '+\
            str(min_row)+' '+str(min_col)+' '+\
            'max row/col: '+str(max_row)+' '+str(max_col)+' '+\
            'shape: '+str(lons.shape))


        #from .spherical import SCoordinate as Coordinate
        #from .spherical import Arc
        from pyresample.spherical_geometry import Coordinate, Arc
        #Calculate the eight possible corners and produce arcs for each pair
        #Corners for top side
        # Right side was failing with Divide by Zero error for NCC data because there was 
        # a single good point in the max_col.  Keep incrementing or decrementing until good.min 
        # doesn't equal good.max 
        good = np.where(~lons[min_row,:].mask)[0]
        tries = 0
        while (tries < 20 and good.min() == good.max()):
            #print 'good.min() can\'t equal good.max() for top side, incrementing min_row! Would have failed with ZeroDivisionError before!'
            min_row += 1
            tries += 1
            good = np.where(~lons[min_row,:].mask)[0]
        top_corners = [Coordinate(*self.get_lonlat(min_row, good.min())),
                       Coordinate(*self.get_lonlat(min_row, good.max()))]
        top_arc = Arc(top_corners[0], top_corners[1])

        #Corners for bottom side
        good = np.where(~lons[max_row,:].mask)[0]
        tries = 0
        while (tries < 20 and good.min() == good.max()):
            #print 'good.min() can\'t equal good.max() for bottom side, decrementing max_row! Would have failed with ZeroDivisionError before!'
            max_row -= 1
            tries += 1
            good = np.where(~lons[max_row,:].mask)[0]
        bot_corners = [Coordinate(*self.get_lonlat(max_row, good.min())),
                       Coordinate(*self.get_lonlat(max_row, good.max()))]
        bot_arc = Arc(bot_corners[0], bot_corners[1])

        #Corners for left side
        good = np.where(~lons[:,min_col].mask)[0]
        tries = 0
        while (tries < 20 and good.min() == good.max()):
            #print 'good.min() can\'t equal good.max() for left side, incrementing min_col! Would have failed with ZeroDivisionError before!'
            min_col += 1
            tries += 1
            good = np.where(~lons[:,min_col].mask)[0]
        left_corners = [Coordinate(*self.get_lonlat(good.min(),min_col)),
                        Coordinate(*self.get_lonlat(good.max(),min_col))]
        left_arc = Arc(left_corners[0], left_corners[1])

        #Corners for right side
        good = np.where(~lons[:,max_col].mask)[0]
        tries = 0
        while (tries < 20 and good.min() == good.max()):
            #print 'good.min() can\'t equal good.max() for right side, decrementing max_col! Would have failed with ZeroDivisionError before!'
            max_col -= 1
            tries += 1
            good = np.where(~lons[:,max_col].mask)[0]
        right_corners = [Coordinate(*self.get_lonlat(good.min(),max_col)),
                         Coordinate(*self.get_lonlat(good.max(),max_col))]
        right_arc = Arc(right_corners[0], right_corners[1])

        #Calculate the four false corners
        _corners = []
        #Top left false corner
        top_intersections = top_arc.intersections(left_arc)
        dists = [inter.distance(top_corners[0]) for inter in top_intersections]
        if dists[0] < dists[1]:
            _corners.append(top_intersections[0])
        else:
            _corners.append(top_intersections[1])
        #Top right false corner
        top_intersections = top_arc.intersections(right_arc)
        dists = [inter.distance(top_corners[1]) for inter in top_intersections]
        if dists[0] < dists[1]:
            _corners.append(top_intersections[0])
        else:
            _corners.append(top_intersections[1])
        #Bottom right false corner
        bot_intersections = bot_arc.intersections(right_arc)
        dists = [inter.distance(bot_corners[1]) for inter in bot_intersections]
        if dists[0] < dists[1]:
            _corners.append(bot_intersections[0])
        else:
            _corners.append(bot_intersections[1])
        #Bottom left false corner
        bot_intersections = bot_arc.intersections(left_arc)
        dists = [inter.distance(bot_corners[0]) for inter in bot_intersections]
        if dists[0] < dists[1]:
            _corners.append(bot_intersections[0])
        else:
            _corners.append(bot_intersections[1])
        return _corners

    def get_bounding_box_lonlats(self,npts=100):
        """Returns array of lon/lats along the bounding Arcs

        :Parameters:
        npts: int
            Number of points to return along each line

        :Returns:
        (top, right, bottom, left) : 4 tuples containing lists 
                                    of len npts of lons/lats
        retval = (list(tplons),list(tplats)),
                 (list(rtlons),list(rtlats)),
                 (list(btlons),list(btlats)),
                 (list(ltlons),list(ltlats))
        
        eg for n=3
           ([tplon0,tplon1,tplon2],[tplat0,tplat1,tplat2]),
           ([rtlon0,rtlon1,rtlon2],[rtlat0,rtlat1,rtlat2]),
           ([btlon0,btlon1,btlon2],[btlat0,btlat1,btlat2]),
           ([ltlon0,ltlon1,ltlon2],[ltlat0,ltlat1,ltlat2]),
        """
        g = Geod(ellps='WGS84')

        # Top of bounding box
        # g.npts returns a list of tuples of lon/lat pairs
        #    [(lon0,lat0),(lon1,lat1),(lon2,lat2)]
        # zip reformats that into 2 tuples of lons and lats
        #    [(lon0,lon1,lon2),(lat0,lat1,lat2)]
        # list(tplons) returns list of lons
        #       [lon0,lon1,lon2]
        # list(tplats) returns list of lats
        #       [lat0,lat1,lat2]
        tplons,tplats = zip(*g.npts(self.corners[0].lon, self.corners[0].lat, 
                    self.corners[1].lon, self.corners[1].lat,
                    npts,radians=True))
        # Right side of bounding box
        rtlons,rtlats = zip(*g.npts(self.corners[1].lon, self.corners[1].lat, 
                      self.corners[2].lon, self.corners[2].lat,
                      npts,radians=True))
        # Bottom of bounding box
        btlons,btlats = zip(*g.npts(self.corners[2].lon, self.corners[2].lat, 
                       self.corners[3].lon, self.corners[3].lat,
                       npts,radians=True))
        # Left side of bounding box
        ltlons,ltlats = zip(*g.npts(self.corners[3].lon, self.corners[3].lat, 
                     self.corners[0].lon, self.corners[0].lat,
                     npts,radians=True))

        retval = [(list(tplons),list(tplats)),
                 (list(rtlons),list(rtlats)),
                 (list(btlons),list(btlats)),
                 (list(ltlons),list(ltlats))]
        return retval


# Use regular pyresample geometry for this. Failed in kd_tree
#class AreaDefinition(BaseDefinition):
#
#    """Holds definition of an area.
#
#    :Parameters:
#    area_id : str 
#        ID of area
#    name : str
#        Name of area
#    proj_id : str 
#        ID of projection
#    proj_dict : dict 
#        Dictionary with Proj.4 parameters
#    x_size : int 
#        x dimension in number of pixels
#    y_size : int     
#        y dimension in number of pixels    
#    area_extent : list 
#        Area extent as a list (LL_x, LL_y, UR_x, UR_y)
#    nprocs : int, optional 
#        Number of processor cores to be used
#    lons : numpy array, optional
#        Grid lons
#    lats : numpy array, optional
#        Grid lats
#
#    :Attributes:
#    area_id : str         
#        ID of area
#    name : str
#        Name of area
#    proj_id : str         
#        ID of projection
#    proj_dict : dict        
#        Dictionary with Proj.4 parameters
#    x_size : int          
#        x dimension in number of pixels
#    y_size : int          
#        y dimension in number of pixels
#    shape : tuple
#        Corresponding array shape as (rows, cols)
#    size : int
#        Number of points in grid
#    area_extent : tuple     
#        Area extent as a tuple (LL_x, LL_y, UR_x, UR_y)
#    area_extent_ll : tuple     
#        Area extent in lons lats as a tuple (LL_lon, LL_lat, UR_lon, UR_lat)
#    pixel_size_x : float    
#        Pixel width in projection units
#    pixel_size_y : float    
#        Pixel height in projection units
#    pixel_upper_left : list 
#        Coordinates (x, y) of center of upper left pixel in projection units
#    pixel_offset_x : float 
#        x offset between projection center and upper left corner of upper 
#        left pixel in units of pixels.
#    pixel_offset_y : float 
#        y offset between projection center and upper left corner of upper 
#        left pixel in units of pixels..
#
#    Properties:
#    proj4_string : str
#        Projection defined as Proj.4 string
#    lons : object
#        Grid lons
#    lats : object
#        Grid lats
#    cartesian_coords : object
#        Grid cartesian coordinates
#    projection_x_coords : object
#        Grid projection x coordinate
#    projection_y_coords : object
#        Grid projection y coordinate
#    """
#
#    def __init__(self, area_id, name, proj_id, proj_dict, x_size, y_size,
#                 area_extent, nprocs=1, lons=None, lats=None, dtype=np.float64):
#        if not isinstance(proj_dict, dict):
#            raise TypeError('Wrong type for proj_dict: %s. Expected dict.'
#                            % type(proj_dict))
#
#        super(AreaDefinition, self).__init__(lons, lats, nprocs)
#        self.area_id = area_id
#        self.name = name
#        self.proj_id = proj_id
#        self.x_size = x_size
#        self.y_size = y_size
#        self.shape = (y_size, x_size)
#        if lons is not None:
#            if lons.shape != self.shape:
#                raise ValueError('Shape of lon lat grid must match '
#                                 'area definition')
#        self.size = y_size * x_size
#        self.ndim = 2
#        self.pixel_size_x = (area_extent[2] - area_extent[0]) / float(x_size)
#        self.pixel_size_y = (area_extent[3] - area_extent[1]) / float(y_size)
#        self.proj_dict = proj_dict
#        self.area_extent = tuple(area_extent)
#
#        # Calculate area_extent in lon lat
#        proj = _spatial_mp.Proj(**proj_dict)
#        corner_lons, corner_lats = proj((area_extent[0], area_extent[2]),
#                                        (area_extent[1], area_extent[3]),
#                                        inverse=True)
#        self.area_extent_ll = (corner_lons[0], corner_lats[0],
#                               corner_lons[1], corner_lats[1])
#
#        # Calculate projection coordinates of center of upper left pixel
#        self.pixel_upper_left = \
#            (float(area_extent[0]) +
#             float(self.pixel_size_x) / 2,
#             float(area_extent[3]) -
#             float(self.pixel_size_y) / 2)
#
#        # Pixel_offset defines the distance to projection center from origen (UL)
#        # of image in units of pixels.
#        self.pixel_offset_x = -self.area_extent[0] / self.pixel_size_x
#        self.pixel_offset_y = self.area_extent[3] / self.pixel_size_y
#
#        self.projection_x_coords = None
#        self.projection_y_coords = None
#
#        self.dtype = dtype
#
#    def __str__(self):
#        # We need a sorted dictionary for a unique hash of str(self)
#        proj_dict = self.proj_dict
#        proj_str = ('{' +
#                    ', '.join(["'%s': '%s'" % (str(k), str(proj_dict[k]))
#                               for k in sorted(proj_dict.keys())]) +
#                    '}')
#        return ('Area ID: %s\nName: %s\nProjection ID: %s\n'
#                'Projection: %s\nNumber of columns: %s\nNumber of rows: %s\n'
#                'Area extent: %s') % (self.area_id, self.name, self.proj_id,
#                                      proj_str, self.x_size, self.y_size,
#                                      self.area_extent)
#
#    __repr__ = __str__
#
#    def __eq__(self, other):
#        """Test for equality"""
#
#        try:
#            return ((self.proj_dict == other.proj_dict) and
#                    (self.shape == other.shape) and
#                    (self.area_extent == other.area_extent))
#        except AttributeError:
#            return super(AreaDefinition, self).__eq__(other)
#
#    def __ne__(self, other):
#        """Test for equality"""
#
#        return not self.__eq__(other)
#
#    def get_xy_from_lonlat(self, lon, lat):
#        """Retrieve closest x and y coordinates (column, row indices) for the
#        specified geolocation (lon,lat) if inside area. If lon,lat is a point a
#        ValueError is raised if the return point is outside the area domain. If
#        lon,lat is a tuple of sequences of longitudes and latitudes, a tuple of
#        masked arrays are returned.
#
#        :Input:
#        lon : point or sequence (list or array) of longitudes
#        lat : point or sequence (list or array) of latitudes
#
#        :Returns:
#        (x, y) : tuple of integer points/arrays
#        """
#
#        if isinstance(lon, list):
#            lon = np.array(lon)
#        if isinstance(lat, list):
#            lat = np.array(lat)
#
#        if ((isinstance(lon, np.ndarray) and
#             not isinstance(lat, np.ndarray)) or
#            (not isinstance(lon, np.ndarray) and
#             isinstance(lat, np.ndarray))):
#            raise ValueError("Both lon and lat needs to be of " +
#                             "the same type and have the same dimensions!")
#
#        if isinstance(lon, np.ndarray) and isinstance(lat, np.ndarray):
#            if lon.shape != lat.shape:
#                raise ValueError("lon and lat is not of the same shape!")
#
#        pobj = _spatial_mp.Proj(self.proj4_string)
#        upl_x = self.area_extent[0]
#        upl_y = self.area_extent[3]
#        xscale = abs(self.area_extent[2] -
#                     self.area_extent[0]) / float(self.x_size)
#        yscale = abs(self.area_extent[1] -
#                     self.area_extent[3]) / float(self.y_size)
#
#        xm_, ym_ = pobj(lon, lat)
#        x__ = (xm_ - upl_x) / xscale
#        y__ = (upl_y - ym_) / yscale
#
#        if isinstance(x__, np.ndarray) and isinstance(y__, np.ndarray):
#            mask = (((x__ < 0) | (x__ > self.x_size)) |
#                    ((y__ < 0) | (y__ > self.y_size)))
#            return (np.ma.masked_array(x__.astype('int'), mask=mask,
#                                       fill_value=-1),
#                    np.ma.masked_array(y__.astype('int'), mask=mask,
#                                       fill_value=-1))
#        else:
#            if ((x__ < 0 or x__ > self.x_size) or
#                    (y__ < 0 or y__ > self.y_size)):
#                raise ValueError('Point outside area:( %f %f)' % (x__, y__))
#            return int(x__), int(y__)
#
#    def get_lonlat(self, row, col):
#        """Retrieves lon and lat values of single point in area grid
#
#        :Parameters:
#        row : int
#        col : int
#
#        :Returns:
#        (lon, lat) : tuple of floats
#        """
#
#        return self.get_lonlats(nprocs=None, data_slice=(row, col))
#
#    def get_proj_coords(self, data_slice=None, cache=False, dtype=None):
#        """Get projection coordinates of grid 
#
#        :Parameters:
#        data_slice : slice object, optional
#            Calculate only coordinates for specified slice
#        cache : bool, optional
#            Store result the result. Requires data_slice to be None
#
#        :Returns: 
#        (target_x, target_y) : tuple of numpy arrays
#            Grids of area x- and y-coordinates in projection units
#        """
#
#        def get_val(val, sub_val, max):
#            # Get value with substitution and wrapping
#            if val is None:
#                return sub_val
#            else:
#                if val < 0:
#                    # Wrap index
#                    return max + val
#                else:
#                    return val
#
#        if self.projection_x_coords is not None and self.projection_y_coords is not None:
#            # Projection coords are cached
#            if data_slice is None:
#                return self.projection_x_coords, self.projection_y_coords
#            else:
#                return self.projection_x_coords[data_slice], self.projection_y_coords[data_slice]
#
#        is_single_value = False
#        is_1d_select = False
#
#        if dtype is None:
#            dtype = self.dtype
#
#        # create coordinates of local area as ndarrays
#        if data_slice is None or data_slice == slice(None):
#            # Full slice
#            rows = self.y_size
#            cols = self.x_size
#            row_start = 0
#            col_start = 0
#        else:
#            if isinstance(data_slice, slice):
#                # Row slice
#                row_start = get_val(data_slice.start, 0, self.y_size)
#                col_start = 0
#                rows = get_val(
#                    data_slice.stop, self.y_size, self.y_size) - row_start
#                cols = self.x_size
#            elif isinstance(data_slice[0], slice) and isinstance(data_slice[1], slice):
#                # Block slice
#                row_start = get_val(data_slice[0].start, 0, self.y_size)
#                col_start = get_val(data_slice[1].start, 0, self.x_size)
#                rows = get_val(
#                    data_slice[0].stop, self.y_size, self.y_size) - row_start
#                cols = get_val(
#                    data_slice[1].stop, self.x_size, self.x_size) - col_start
#            elif isinstance(data_slice[0], slice):
#                # Select from col
#                is_1d_select = True
#                row_start = get_val(data_slice[0].start, 0, self.y_size)
#                col_start = get_val(data_slice[1], 0, self.x_size)
#                rows = get_val(
#                    data_slice[0].stop, self.y_size, self.y_size) - row_start
#                cols = 1
#            elif isinstance(data_slice[1], slice):
#                # Select from row
#                is_1d_select = True
#                row_start = get_val(data_slice[0], 0, self.y_size)
#                col_start = get_val(data_slice[1].start, 0, self.x_size)
#                rows = 1
#                cols = get_val(
#                    data_slice[1].stop, self.x_size, self.x_size) - col_start
#            else:
#                # Single element select
#                is_single_value = True
#
#                row_start = get_val(data_slice[0], 0, self.y_size)
#                col_start = get_val(data_slice[1], 0, self.x_size)
#
#                rows = 1
#                cols = 1
#
#        # Calculate coordinates
#        target_x = np.fromfunction(lambda i, j: (j + col_start) *
#                                   self.pixel_size_x +
#                                   self.pixel_upper_left[0],
#                                   (rows,
#                                    cols), dtype=dtype)
#
#        target_y = np.fromfunction(lambda i, j:
#                                   self.pixel_upper_left[1] -
#                                   (i + row_start) * self.pixel_size_y,
#                                   (rows,
#                                    cols), dtype=dtype)
#
#        if is_single_value:
#            # Return single values
#            target_x = float(target_x)
#            target_y = float(target_y)
#        elif is_1d_select:
#            # Reshape to 1D array
#            target_x = target_x.reshape((target_x.size,))
#            target_y = target_y.reshape((target_y.size,))
#
#        if cache and data_slice is None:
#            # Cache the result if requested
#            self.projection_x_coords = target_x
#            self.projection_y_coords = target_y
#
#        return target_x, target_y
#
#    @property
#    def proj_x_coords(self):
#        return self.get_proj_coords(data_slice=(0, slice(None)))[0]
#
#    @property
#    def proj_y_coords(self):
#        return self.get_proj_coords(data_slice=(slice(None), 0))[1]
#
#    @property
#    def outer_boundary_corners(self):
#        """Returns the lon,lat of the outer edges of the corner points
#        """
#        ### Original 
#        from pyresample.spherical_geometry import Coordinate
#        proj = _spatial_mp.Proj(**self.proj_dict)
#
#        corner_lons, corner_lats = proj((self.area_extent[0], self.area_extent[2],
#                                         self.area_extent[2], self.area_extent[0]),
#                                        (self.area_extent[3], self.area_extent[3],
#                                         self.area_extent[1], self.area_extent[1]),
#                                        inverse=True)
#        return [Coordinate(corner_lons[0], corner_lats[0]),
#                Coordinate(corner_lons[1], corner_lats[1]),
#                Coordinate(corner_lons[2], corner_lats[2]),
#                Coordinate(corner_lons[3], corner_lats[3])]
#        ### End Original
##        from .spherical import SCoordinate
##        log.info('RUNNING SPHERICAL in outer_boundary_corners')
##        proj = _spatial_mp.Proj(**self.proj_dict)
##
##        corner_lons, corner_lats = proj((self.area_extent[0], self.area_extent[2],
##                                         self.area_extent[2], self.area_extent[0]),
##                                        (self.area_extent[3], self.area_extent[3],
##                                         self.area_extent[1], self.area_extent[1]),
##                                        inverse=True)
##        return [SCoordinate(corner_lons[0], corner_lats[0]),
##                SCoordinate(corner_lons[1], corner_lats[1]),
##                SCoordinate(corner_lons[2], corner_lats[2]),
##                SCoordinate(corner_lons[3], corner_lats[3])]
#
#    def get_lonlats(self, nprocs=None, data_slice=None, cache=False, dtype=None):
#        """Returns lon and lat arrays of area.
#
#        :Parameters:        
#        nprocs : int, optional 
#            Number of processor cores to be used.
#            Defaults to the nprocs set when instantiating object
#        data_slice : slice object, optional
#            Calculate only coordinates for specified slice
#        cache : bool, optional
#            Store result the result. Requires data_slice to be None
#
#        :Returns: 
#        (lons, lats) : tuple of numpy arrays
#            Grids of area lons and and lats
#        """
#
#        if dtype is None:
#            dtype = self.dtype
#
#        if self.lons is None or self.lats is None:
#            #Data is not cached
#            if nprocs is None:
#                nprocs = self.nprocs
#
#            # Proj.4 definition of target area projection
#            if nprocs > 1:
#                target_proj = _spatial_mp.Proj_MP(**self.proj_dict)
#            else:
#                target_proj = _spatial_mp.Proj(**self.proj_dict)
#
#            # Get coordinates of local area as ndarrays
#            target_x, target_y = self.get_proj_coords(
#                data_slice=data_slice, dtype=dtype)
#
#            # Get corresponding longitude and latitude values
#            lons, lats = target_proj(target_x, target_y, inverse=True,
#                                     nprocs=nprocs)
#            lons = np.asanyarray(lons, dtype=dtype)
#            lats = np.asanyarray(lats, dtype=dtype)
#
#            if cache and data_slice is None:
#                # Cache the result if requested
#                self.lons = lons
#                self.lats = lats
#
#            # Free memory
#            del(target_x)
#            del(target_y)
#        else:
#            #Data is cached
#            if data_slice is None:
#                # Full slice
#                lons = self.lons
#                lats = self.lats
#            else:
#                lons = self.lons[data_slice]
#                lats = self.lats[data_slice]
#
#        return lons, lats
#
#    @property
#    def proj4_string(self):
#        """Returns projection definition as Proj.4 string"""
#
#        items = self.proj_dict.items()
#        return '+' + ' +'.join([t[0] + '=' + t[1] for t in items])

# MLS maybe implement this eventually? 
class PlanarPolygonDefinition(CoordinateDefinition):

    def get_bounding_box_lonlats(self,npts=100):
        """Returns array of lon/lats along the bounding 
            lat/lon lines

        :Parameters:
        npts: int
            Number of points to return along each line

        :Returns:
        (top, right, bottom, left) : 4 tuples containing lists 
                                    of len npts of lons/lats
        retval = (list(tplons),list(tplats)),
                 (list(rtlons),list(rtlats)),
                 (list(btlons),list(btlats)),
                 (list(ltlons),list(ltlats))
        
        eg for n=3
           ([tplon0,tplon1,tplon2],[tplat0,tplat1,tplat2]),
           ([rtlon0,rtlon1,rtlon2],[rtlat0,rtlat1,rtlat2]),
           ([btlon0,btlon1,btlon2],[btlat0,btlat1,btlat2]),
           ([ltlon0,ltlon1,ltlon2],[ltlat0,ltlat1,ltlat2]),
        """

        # Top of bounding box
        tplons = np.linspace(self.corners[0].lon,self.corners[1].lon,npts)
        tplats = np.linspace(self.corners[0].lat,self.corners[1].lat,npts)
        # Right side of bounding box
        rtlons = np.linspace(self.corners[1].lon,self.corners[2].lon,npts)
        rtlats = np.linspace(self.corners[1].lat,self.corners[2].lat,npts)
        # Bottom of bounding box
        btlons = np.linspace(self.corners[2].lon,self.corners[3].lon,npts)
        btlats = np.linspace(self.corners[2].lat,self.corners[3].lat,npts)
        # Left side of bounding box
        ltlons = np.linspace(self.corners[3].lon,self.corners[0].lon,npts)
        ltlats = np.linspace(self.corners[3].lat,self.corners[0].lat,npts)

        retval = [(list(tplons),list(tplats)),
                 (list(rtlons),list(rtlats)),
                 (list(btlons),list(btlats)),
                 (list(ltlons),list(ltlats))]
        return retval


    @property
    def corners(self):
        #print '    In 2D false corners for: '+str(self.name)
        try:
            #print '        Corners already set, returning'
            return super(CoordinateDefinition, self).corners
        except ValueError:
            pass

        return get_2d_false_corners(self)


    def __contains__(self, point):
        """Is a point inside the 4 corners of the current area? This 
            DOES NOT use spherical geometry / great circle arcs.
        """ 
        corners = self.corners

        if isinstance(point, tuple):
            retval = planar_point_inside(Coordinate(*point), corners)
        else:
            retval = planar_point_inside(point, corners)

        #print '        retval from FALSE CORNERS contains '+str(retval)

        return retval

    def intersection(self, other):
        """Returns the corners of the intersection polygon of the current area
        with *other*.

        :Parameters:
        other : object
            Instance of subclass of BaseDefinition

        :Returns:
        (corner1, corner2, corner3, corner4) : tuple of points
        """
        
        self_corners = self.corners

        other_corners = get_2d_false_corners(other)

        #shell()

        return planar_intersection_polygon(self_corners,other_corners)

    def overlaps_minmaxlatlon(self,other):
        log.info('PlanarPolygonDefinition overlaps_minmaxlatlon')
        return self.overlaps(other)

    def overlaps(self, other):
        """Tests if the current area overlaps the *other* area. This is based
        solely on the corners of areas, assuming the boundaries to be straight
        lines.

        :Parameters:
        other : object
            Instance of subclass of BaseDefinition

        :Returns:
        overlaps : bool
        """

        self_corners = self.corners
        other_corners = get_2d_false_corners(other)

        log.info('    PlanarPolygon Overlaps Self False Corners: '+str(self_corners))
        log.info('    PlanarPolygon Overlaps Other False Corners: '+str(other_corners))

        # Previously just did if i in other or if i in self.
        # This does not take 2d_false_corners into account
        # when doing i in *area_definition* (because it uses
        # area_definition.__contains__, which does not use
        # planar_point_inside, but spherical point_inside.
        for i in self_corners:
            if planar_point_inside(i,other_corners):
                log.info('    Point '+str(i)+' in other')
                return True
        for i in other_corners:
            if planar_point_inside(i,self_corners):
                log.info('    Point '+str(i) +' in self')
                return True

        self_line1 = Line(self_corners[0], self_corners[1])
        self_line2 = Line(self_corners[1], self_corners[2])
        self_line3 = Line(self_corners[2], self_corners[3])
        self_line4 = Line(self_corners[3], self_corners[0])

        other_line1 = Line(other_corners[0], other_corners[1])
        other_line2 = Line(other_corners[1], other_corners[2])
        other_line3 = Line(other_corners[2], other_corners[3])
        other_line4 = Line(other_corners[3], other_corners[0])

        for i in (self_line1, self_line2, self_line3, self_line4):
            for j in (other_line1, other_line2, other_line3, other_line4):
                if i.intersects(j):
                    return True
        return False

class Line(object):

    """A Line between two lat/lon points.
    """
    start = None
    end = None

    def __init__(self, start, end):
        self.start, self.end = start, end

    def __eq__(self, other):
        if(abs(self.start.lon-other.start.lon) < EPSILON and 
            abs(self.end.lon-other.end.lon)<EPSILON and
            abs(self.start.lat - other.start.lat) < EPSILON and
            abs(self.end.lat - other.end.lat) < EPSILON):
            return 1
        return 0

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return (str(self.start) + " -> " + str(self.end))

    def __repr__(self):
        return (str(self.start) + " -> " + str(self.end))

    def intersects(self, other_line):
        """Says if two lines defined by the current line and the *other_line*
        intersect. A line is defined as the shortest tracks between two points.
        """
        intpt= self.intersection(other_line)
        return bool(intpt)

    def intersection(self, other):
        """Says where, if two lines defined by the current line and the
        *other_line* intersect. 
        """
        log.info('self: '+str(self)+' other: '+str(other))
        if self == other:
            # Used to be return True, that is definitely not right (expects Coordinate)
            # Do we want start or end ? Does it matter? Lines are the same, everything is
            # an intersection.
            return self.start
        # If any of the start/end points match, return that point.
        if self.end==other.start or self.end == other.end:
            return self.end 
        if self.start==other.start or self.start == other.end: 
            return self.start

        # Line equation: y = mx + b
        # m = (y2-y1)/(x2-x1)
        # B_self = y - M_self*x
        # Pick any x/y on the line - try end point
        # B_self = self.end.lat - M_self*self.end.lon
        # B_other = other.end.lat - M_self*self.end.lon
        from pyresample.spherical_geometry import Coordinate

        selfendlon = self.end.lon
        selfstartlon = self.start.lon
        otherendlon = other.end.lon
        otherstartlon = other.start.lon
        # Not sure if this is necessary, or good...
#        if self.end.lon < 0:
#            selfendlon = self.end.lon + 2*math.pi
#        if self.start.lon < 0:
#            selfstartlon = self.start.lon + 2*math.pi
#        if other.end.lon < 0:
#            otherendlon = other.end.lon + 2*math.pi
#        if other.start.lon < 0:
#            otherstartlon = other.start.lon + 2*math.pi

        log.info('    self lons: '+str(math.degrees(selfstartlon))+' '+str(math.degrees(selfendlon))+' other lons: '+str(math.degrees(otherstartlon))+' '+str(math.degrees(otherendlon)))

        # If both vertical, will be no intersection
        if abs(selfendlon - selfstartlon) < EPSILON and abs(otherendlon - otherstartlon) < EPSILON:
            log.info('    Both vertical, no intersection')
            return None
        # If self is vertical, but not parallel, intersection will be selfstartlon and lat = Mother*lon+B_other
        if abs(selfendlon - selfstartlon) < EPSILON:
            lon = selfstartlon
            M_other = (other.end.lat - other.start.lat)/(otherendlon-otherstartlon)
            B_other = other.end.lat - M_other*otherendlon
            lat = M_other*lon+B_other
            log.info('    self is vertical')
            #Make sure it falls within the segment and not outside.
            # Previously was only checking lat, need to 
            # also check lon or opposite side of world would match
            if (lat > min([self.end.lat,self.start.lat]) and 
                lat < max([self.end.lat,self.start.lat]) and
                lon > min([otherendlon,otherstartlon]) and
                lon < max([otherendlon,otherstartlon])):
                log.info('        and intersects')
                # Apparently Coordinate takes degrees ??? And must be -180 to 180 ?!
                # MLS use wrap_longitudes?
                if lon > math.pi:
                    lon -= 2*math.pi
                return Coordinate(math.degrees(lon),math.degrees(lat))
            else:
                return None
        # same for other
        if abs(otherendlon - otherstartlon) < EPSILON:
            lon = otherstartlon
            M_self = (self.end.lat - self.start.lat)/(selfendlon-selfstartlon)
            B_self = self.end.lat - M_self*selfendlon
            lat = M_self*lon+B_self
            log.info('    other is vertical')
            #Make sure it falls within the segment and not outside.
            # Previously was only checking lat, need to 
            # also check lon or opposite side of world would match
            if (lat > min([other.end.lat,other.start.lat]) and 
                lat < max([other.end.lat,other.start.lat]) and 
                lon > min([selfendlon,selfstartlon]) and
                lon < max([selfendlon,selfstartlon])):
                log.info('        and intersects')
                # Apparently Coordinate takes degrees ??? And must be -180 to 180 ?!
                # MLS Use wrap_longitudes?
                if lon > math.pi:
                    lon -= 2*math.pi
                return Coordinate(math.degrees(lon),math.degrees(lat))
            else:
                return None

    

        # Get slopes of the lines 
        M_self = (self.end.lat - self.start.lat)/(selfendlon-selfstartlon)
        M_other = (other.end.lat - other.start.lat)/(otherendlon-otherstartlon)
    
        # If they are parallel, no intersection
        if (M_self-M_other) < EPSILON:
            log.info('    self and other are parallel, no intersection')
            return None

        # Get the y-intercepts of the lines  
        B_self = self.end.lat - M_self*selfendlon
        B_other = other.end.lat - M_other*otherendlon

        # Solve the equation
        # y=m1x+b1 and y=m2x+b2, equate y's so m1x+b1=m2x+b2, x = (b1-b2)/(m2-m1)
        # equate x's so x=(y-b1)/m1=(y-b2)/m2, y = (b1m2-b2m1)/(m2-m1)
        lon = (B_self - B_other)/(M_other - M_self)
        lat = (B_self*M_other - B_other*M_self)/(M_other-M_self)

        # Make sure lat/lon intersects within the line segment, and not outside.
        if (lat > min([other.end.lat,other.start.lat]) and 
            lat < max([other.end.lat,other.start.lat]) and
            lon > min([otherendlon,otherstartlon]) and 
            lon < max([otherendlon,otherstartlon]) and
            lat > min([self.end.lat,self.start.lat]) and 
            lat < max([self.end.lat,self.start.lat]) and
            lon > min([selfendlon,selfstartlon]) and 
            lon < max([selfendlon,selfstartlon])):
            log.info('    self and other intersect within segment')
            # Apparently Coordinate takes degrees ??? And must be -180 to 180 ?!
            # MLS use wrap longitudes?
            if lon > math.pi:
                lon -= 2*math.pi
            return Coordinate(math.degrees(lon),math.degrees(lat))
        else:
            log.info('    self and other intersect, but not within segment')
            return None

def get_2d_false_corners(box_def):
    #print '    In 2D false corners for: '+str(box_def.name)

    min_row = 0
    max_row = -1
    min_col = 0 
    max_col = -1
    side1 = box_def.get_lonlats(data_slice=(min_row, slice(None)))
    side2 = box_def.get_lonlats(data_slice=(slice(None), max_col))
    side3 = box_def.get_lonlats(data_slice=(max_row, slice(None)))
    side4 = box_def.get_lonlats(data_slice=(slice(None), min_col))

    tries = 0
    while (tries < 500 and np.ma.count(box_def.get_lonlats(data_slice=(min_row, slice(None)))[1]) < 10):
        min_row += 1
        tries += 1
    if tries:
        side1 = box_def.get_lonlats(data_slice=(min_row+1, slice(None)))
        log.info('Needed some data in side 1, incremented slice number '+str(tries)+' times. Now have '+str(np.ma.count(side1[1]))+' valid of '+str(np.ma.count(side1[1].mask)))

    tries = 0
    while (tries < 500 and np.ma.count(box_def.get_lonlats(data_slice=(slice(None), max_col))[0]) < 10):
        max_col -= 1
        tries += 1
    if tries:
        side2 = box_def.get_lonlats(data_slice=(slice(None), max_col-1))
        log.info('Needed some data in side 2, decremented slice number '+str(tries)+' times. Now have '+str(np.ma.count(side2[0]))+' valid of '+str(np.ma.count(side2[0].mask)))

    tries = 0
    while (tries < 500 and np.ma.count(box_def.get_lonlats(data_slice=(max_row, slice(None)))[0]) < 10):
        max_row -= 1
        tries += 1
    if tries:
        side3 = box_def.get_lonlats(data_slice=(max_row-1, slice(None)))
        log.info('Needed some data in side 3, decremented slice number '+str(tries)+' times. Now have '+str(np.ma.count(side3[0]))+' valid of '+str(np.ma.count(side3[0].mask)))

    tries = 0
    while (tries < 500 and np.ma.count(box_def.get_lonlats(data_slice=(slice(None), min_col))[1]) < 10):
        min_col += 1
        tries += 1
    if tries:
        side4 = box_def.get_lonlats(data_slice=(slice(None), min_col+1))
        log.info('Needed some data in side 4, incremented slice number '+str(tries)+' times. Now have '+str(np.ma.count(side4[1]))+' valid of '+str(np.ma.count(side4[1].mask)))

    #shell()
        
    # These all need to maintain mask.
    selflons = np.ma.concatenate((side1[0],side2[0],side3[0],side4[0]))
    selflons = np.ma.where(selflons<0,selflons+360,selflons)
    # MLS use wrap_longitudes? Figure out prime meridian vs dateline...
    #if side4[0].min() > side2[0].max():
    #    selflons = np.ma.where(selflons<0,selflons+360,selflons)
    selflats = np.ma.concatenate((side1[1],side2[1],side3[1],side4[1]))

    #self_corners = self.corners
    #other_corners = other.corners
    minlon = selflons.min()
    maxlon = selflons.max()
    # MLS use wrap_longitudes?
    if minlon > 180:
        minlon -= 360
    if maxlon > 180:
        maxlon -= 360
    minlat = selflats.min()
    maxlat = selflats.max()

    #print 'IN PlanarPolygonDefinition CORNERS for '+box_def.name+\
    #    ' min/max lat min/max lon:'+\
    #    str(minlat)+' '+str(maxlat)+' '+str(minlon)+' '+str(maxlon)

    from pyresample.spherical_geometry import Coordinate

    return [Coordinate(minlon,maxlat),
                Coordinate(maxlon,maxlat),
                Coordinate(maxlon,minlat),
                Coordinate(minlon,minlat)] 

def planar_intersection_polygon(area_corners, segment_corners):
    """Get the intersection polygon between two areas.
    """
    # First test each 
    lons = np.array([])
    lats = np.array([])
    for segment_corner in segment_corners:
        if planar_point_inside(segment_corner,area_corners):
            currlon = segment_corner.lon
            # MLS use wrap_longitudes?
            if currlon < 0:
                currlon += 2*math.pi
            lons = np.concatenate((lons,[currlon]))
            lats = np.concatenate((lats,[segment_corner.lat]))
            log.info('Adding intersection from segment '+str(segment_corner))
    for area_corner in area_corners:
        if planar_point_inside(area_corner,segment_corners):
            currlon = area_corner.lon
            # MLS use wrap_longitudes?
            if currlon < 0:
                currlon += 2*math.pi
            lons = np.concatenate((lons,[currlon]))
            lats = np.concatenate((lats,[area_corner.lat]))
            log.info('Adding intersection from area '+str(area_corner))

    area_line1 = Line(area_corners[0], area_corners[1])
    area_line2 = Line(area_corners[1], area_corners[2])
    area_line3 = Line(area_corners[2], area_corners[3])
    area_line4 = Line(area_corners[3], area_corners[0])

    segment_line1 = Line(segment_corners[0], segment_corners[1])
    segment_line2 = Line(segment_corners[1], segment_corners[2])
    segment_line3 = Line(segment_corners[2], segment_corners[3])
    segment_line4 = Line(segment_corners[3], segment_corners[0])

    for i in (area_line1, area_line2, area_line3, area_line4):
        for j in (segment_line1, segment_line2, segment_line3, segment_line4):
            intersect = i.intersection(j)
            if intersect:
                log.info('Adding actual intersection '+str(intersect))
                currlon = intersect.lon
                # MLS use wrap_longitudes?
                if intersect.lon < 0:
                    currlon += 2*math.pi
                lons = np.concatenate((lons,[currlon]))
                lats = np.concatenate((lats,[intersect.lat]))

    minlon = math.degrees(lons.min())
    maxlon = math.degrees(lons.max())
    minlat = math.degrees(lats.min())
    maxlat = math.degrees(lats.max())
    # Coordinate MUST be between -180 and 180
    # MLS use wrap_longitudes?
    if minlon > 180:
        minlon -= 180
    if maxlon > 180:
        maxlon -= 180
    from pyresample.spherical_geometry import Coordinate
    return [Coordinate(minlon,maxlat),
                Coordinate(maxlon,maxlat),
                Coordinate(maxlon,minlat),
                Coordinate(minlon,minlat)] 

#    for seg_pt in seg_pts_in_area:
#            
#        
#            
#        
#
#def planar_point_inside(point, boxdef):
def planar_point_inside(point, corners):
    """Is a point inside the 4 corners ? This DOES NOT USE great circle arcs as area
    boundaries.
    """
#    lons = boxdef.get_lonlats()[0]
    lons = np.ma.array([corn.lon for corn in corners])
    lats = np.ma.array([corn.lat for corn in corners])
    # MLS use wrap_longitudes?
    lons = np.ma.where(lons<0,lons+2*math.pi,lons)
            
#    lats = boxdef.get_lonlats()[1]
#    corners = boxdef.corners
    minlon = lons.min()
    maxlon = lons.max()
    minlat = lats.min()
    maxlat = lats.max()
    # MLS use wrap_longitudes?
    if point.lon < 0:
        point.lon += 2*math.pi
#    print '    IN PlanarPolygonDefinition point_inside!!! '+\
#        ' point: '+str(point)+' '+str(math.degrees(minlat))+' '+str(math.degrees(maxlat))+' '+str(math.degrees(minlon))+' '+str(math.degrees(maxlon))
#        ' point: '+str(point)+'\n'+\
#        'c0 '+str(corners[0])+'\n'+\
#        'c1 '+str(corners[1])+'\n'+\
#        'c2 '+str(corners[2])+'\n'+\
#        'c3 '+str(corners[3])+'\n'+\
#        str(minlat)+' '+str(maxlat)+' '+str(minlon)+' '+str(maxlon)
    # MLS 20160405 NOTE point prints degrees for str, but point.lon and point.lat are stored as radians.
    # minlon/maxlon also radians. This is why big sectors were failing, after fixing the
    # "other side of the world" problem.
    # Also, Coordinate takes degrees when passing it a lat lon, just for fun.
    if minlon < point.lon < maxlon and minlat < point.lat < maxlat:
        return True
    return False


def _get_slice(segments, shape):
    """Generator for segmenting a 1D or 2D array"""

    if not (1 <= len(shape) <= 2):
        raise ValueError('Cannot segment array of shape: %s' % str(shape))
    else:
        size = shape[0]
        slice_length = np.ceil(float(size) / segments)
        start_idx = 0
        end_idx = slice_length
        while start_idx < size:
            if len(shape) == 1:
                yield slice(start_idx, end_idx)
            else:
                yield (slice(start_idx, end_idx), slice(None))
            start_idx = end_idx
            end_idx = min(start_idx + slice_length, size)


def _flatten_cartesian_coords(cartesian_coords):
    """Flatten array to (n, 3) shape"""

    shape = cartesian_coords.shape
    if len(shape) > 2:
        cartesian_coords = cartesian_coords.reshape(shape[0] *
                                                    shape[1], 3)
    return cartesian_coords


def _get_highest_level_class(obj1, obj2):
    if (not issubclass(obj1.__class__, obj2.__class__) or
            not issubclass(obj2.__class__, obj1.__class__)):
        raise TypeError('No common superclass for %s and %s' %
                        (obj1.__class__, obj2.__class__))

    if obj1.__class__ == obj2.__class__:
        klass = obj1.__class__
    elif issubclass(obj1.__class__, obj2.__class__):
        klass = obj2.__class__
    else:
        klass = obj1.__class__
    return klass
