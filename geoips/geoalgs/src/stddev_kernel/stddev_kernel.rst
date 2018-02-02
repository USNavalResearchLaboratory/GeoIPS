Standard Deviation Kernel
+++++++++++++++++++++++++
This function is largely included for convenience.  It is used in multiple different algorithms
to perform a windowed standard deviation.  This function is better explained by example.

Say we have a 10x10 array called `dat`, and we want to know the standard deviation in the 3x3
window around each value.  We would issue a call of the form:

.. code-block:: python

    datout = stddev_kernel(dat, 3, 3)

:func:`stddev_kernel <geoalgs.stddev_kernel>` will always return an array of the same size as the input
data array.  Any time we are missing a part of the window such as when we are on an edge or a corner
the standard deviation will be calculated using only the available good values.

.. function:: geoalgs.stddev_kernel(datin, wlines, wsamples[, lines, samples])
    :noindex:

    :param datin: 2-D array of input values *(lines, samples)*
    :type datin: array of floats
    :param wlines: Size of the window to use in the lines direction
    :type wlines: int
    :param wsamples: Size of the window to use in the samples direction
    :type wsamples: int
    :param lines: Number of lines in the input arrays
    :type lines: int or assumed
    :param samples: Number of samples in the input arrays
    :type samples: int or assumed
