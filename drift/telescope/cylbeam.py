import numpy as np

from cosmoutils import coord, cubicspline


def polpattern(angpos, dipole):
    """Calculate the unit polarisation vectors at each position on the sphere
    for a dipole direction.a

    Parameters
    ----------
    angpos : np.ndarray[npoints, 2]
        The positions on the sphere to calculate at.
    dipole : np.ndarray[2 or 3]
        The unit vector for the dipole direction. If length is 2, assume in
        vector is in spherical polars, if 3 it's cartesian.

    Returns
    -------
    vectors : np.ndarray[npoints, 2]
        Vector at each point in thetahat, phihat basis.
    """

    if dipole.shape[0] == 2:
        dipole = coord.sph_to_cart(dipole)

    thatp, phatp = coord.thetaphi_plane_cart(angpos)

    polvec = np.zeros(angpos.shape[:-1] + (2,), dtype=angpos.dtype)

    # Calculate components by projecting into basis.
    polvec[..., 0] = np.dot(thatp, dipole)
    polvec[..., 1] = np.dot(phatp, dipole)

    # Normalise length to unity.
    polvec = polvec * (np.sum(polvec**2, axis=-1)**-0.5)[..., np.newaxis]

    return polvec





def beam_dipole(theta, phi, squint):
    """Beam for a dipole above a ground plane.
    """
    return ((1 - np.sin(theta)**2 * np.sin(phi)**2)**(squint/2)
        * np.sin(0.5 * np.pi * np.cos(theta)))


def beam_exptan(theta, fwhm):
    """ExpTan beam.

    Parameters
    ----------
    theta : array_like
        Array of angles to return beam at.
    fwhm : scalar
        Beam width at half power (note that the beam returned is amplitude).

    Returns
    -------
    beam : array_like
        The amplitude beam at each requested angle.
    """
    alpha = np.log(2.0) / (2*np.tan(fwhm / 2.0)**2)

    return np.exp(-alpha*np.tan(theta)**2)



def fraunhofer_cylinder(antenna_func, width, res=1.0):
    """Calculate the Fraunhofer diffraction pattern for a feed illuminating a
    cylinder (in 1D).

    Parameters
    ----------
    antenna_func : function(theta) -> amplitude
        Function describing the antenna amplitude pattern as a function of angle.
    width : scalar
        Cylinder width in wavelengths.
    res : scalar, optional
        Resolution boost factor (default is 1.0)

    Returns
    -------
    beam : function(sintheta) -> amplitude
        The beam pattern, normalised to have unit maximum.
    """
    res = int(res * 16)
    num = 512
    hnum = 512/2 -1

    ua = -1.0 * np.linspace(-1.0, 1.0, num, endpoint=False)[::-1]

    ax = antenna_func(2*np.arctan(ua))

    axe = np.zeros(res*num)

    axe[:(hnum+2)] = ax[hnum:]
    axe[-hnum:] = ax[:hnum]


    fx = np.fft.fft(axe).real

    kx = 2 * np.fft.fftfreq(res*num, ua[1] - ua[0]) / width

    fx = np.fft.fftshift(fx) / fx.max()
    kx = np.fft.fftshift(kx)

    return cubicspline.Interpolater(kx, fx)





def beam_amp(angpos, zenith, width, fwhm_x, fwhm_y):
    """Beam amplitude across the sky.

    Parameters
    ----------
    angpos : np.ndarray[npoints]
        Angular position on the sky.
    zenith : np.ndarray[2]
        Position of zenin on spherical polars.
    width : scalar
        Cylinder width in wavelengths.
    fwhm_x, fwhm_y
        Full with at half power in the x and y directions.

    Returns
    -------
    beam : np.ndarray[npoints]
        Amplitude of beam at each point.
    """
    yhat, xhat = coord.thetaphi_plane_cart(zenith)

    xplane = lambda t: beam_exptan(t, fwhm_x)
    yplane = lambda t: beam_exptan(t, fwhm_y)

    beampat = fraunhofer_cylinder(xplane, width)

    cvec = coord.sph_to_cart(angpos)
    horizon = (np.dot(cvec, coord.sph_to_cart(zenith)) > 0.0).astype(np.float64)

    ew_amp = beampat(np.dot(cvec, xhat))
    ns_amp = yplane(np.arcsin(np.dot(cvec, yhat)))

    return (ew_amp * ns_amp * horizon)


def beam_x(angpos, zenith, width, fwhm_e, fwhm_h):
    """Beam amplitude across the sky for the X dipole (points E).

    Using ExpTan model.

    Parameters
    ----------
    angpos : np.ndarray[npoints]
        Angular position on the sky.
    zenith : np.ndarray[2]
        Position of zenin on spherical polars.
    width : scalar
        Cylinder width in wavelengths.
    fwhm_e, fwhm_h
        Full with at half power in the E and H planes of the antenna.

    Returns
    -------
    beam : np.ndarray[npoints, 2]
        Amplitude vector of beam at each point (in thetahat, phihat)
    """
    xhat = coord.thetaphi_plane_cart(zenith)[1]
    pvec = polpattern(angpos, xhat)

    amp = beam_amp(angpos, zenith, width, fwhm_e, fwhm_h)

    return amp[:, np.newaxis] * pvec


def beam_y(angpos, zenith, width, fwhm_e, fwhm_h):
    """Beam amplitude across the sky for the Y dipole (points N).

    Using ExpTan model.

    Parameters
    ----------
    angpos : np.ndarray[npoints]
        Angular position on the sky.
    zenith : np.ndarray[2]
        Position of zenin on spherical polars.
    width : scalar
        Cylinder width in wavelengths.
    fwhm_e, fwhm_h
        Full with at half power in the E and H planes of the antenna.

    Returns
    -------
    beam : np.ndarray[npoints, 2]
        Amplitude vector of beam at each point (in thetahat, phihat)
    """
    # Reverse as thetahat points south
    yhat = -1.0 * coord.thetaphi_plane_cart(zenith)[0]
    pvec = polpattern(angpos, yhat)

    amp = beam_amp(angpos, zenith, width, fwhm_h, fwhm_e)

    return amp[:, np.newaxis] * pvec