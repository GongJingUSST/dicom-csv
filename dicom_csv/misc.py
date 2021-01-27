import os
import warnings
from operator import itemgetter
from os.path import join as jp

import numpy as np

from .utils import *

__all__ = 'get_image', 'stack_images'


def get_image(instance: Dataset):
    def _to_int(x):
        if x == int(x):
            x = int(x)
        return x

    array = instance.pixel_array
    slope, intercept = instance.get('RescaleSlope'), instance.get('RescaleIntercept')
    if slope is not None and slope != 1:
        array = array * _to_int(slope)
    if intercept is not None and intercept != 0:
        array = array + _to_int(intercept)

    return array


def stack_images(series: Series, axis: int = -1):
    return np.moveaxis(np.array(list(map(get_image, series))), 0, axis)


# TODO: legacy support
class Default:
    pass


# TODO: move to pathlib
@np.deprecate
def load_series(row: pd.Series, base_path: PathLike = None, orientation: Union[bool, None] = Default,
                scaling: bool = None) -> np.ndarray:
    """
    Loads an image based on its ``row`` in the metadata dataframe.

    If ``base_path`` is not None, PathToFolder is assumed to be relative to it.

    If ``orientation`` is True, the loaded image will be transposed and flipped
    to standard (Coronal, Sagittal, Axial) orientation. If None, the orientation
    will be standardized only if possible (i.e. all the necessary metadata is present).

    Required columns: PathToFolder, FileNames.
    """
    if orientation is Default:
        orientation = None
        warnings.warn('The default value for `orientation` will be changed to `False` in next releases. '
                      'Pass orientation=None, if you wish to keep the old behaviour.', UserWarning)

    folder, files = row.PathToFolder, row.FileNames.split('/')
    if base_path is not None:
        folder = os.path.join(base_path, folder)
    if contains_info(row, 'InstanceNumbers'):
        files = map(itemgetter(1), sorted(zip_equal(split_floats(row.InstanceNumbers), files)))

    x = np.stack([dcmread(jp(folder, file)).pixel_array for file in files], axis=-1)

    if scaling and not contains_info(row, 'RescaleSlope', 'RescaleIntercept'):
        raise ValueError('Not enough information for scaling.')
    if scaling is not False and contains_info(row, 'RescaleSlope'):
        x = x * row.RescaleSlope
    if scaling is not False and contains_info(row, 'RescaleIntercept'):
        x = x + row.RescaleIntercept

    if orientation is None:
        orientation = contains_info(row, *ORIENTATION)
    if orientation:
        from .spatial import normalize_orientation
        x = normalize_orientation(x, row)

    return x
