import numpy as np
import pytest

from btrack import btypes, utils


def _make_test_image(
    boxsize: int = 150,
    ndim: int = 2,
    nobj: int = 10,
    binsize: int = 5,
    binary: bool = True,
):
    """Make a test image that ensures that no two pixels are in contact."""
    shape = (boxsize,) * ndim
    img = np.zeros(shape, dtype=np.uint16)

    # return an empty image if we have no objects
    if nobj == 0:
        return img, None

    # split this into voxels
    bins = boxsize // binsize

    def _sample():
        _img = np.zeros((binsize,) * ndim, dtype=np.uint16)
        _coord = tuple(
            np.random.randint(1, binsize - 1, size=(ndim,)).tolist()
        )
        _img[_coord] = 1
        assert np.sum(_img) == 1
        return _img, _coord

    # now we update nobj grid positions with a sample
    grid = np.stack(np.meshgrid(*[np.arange(bins)] * ndim), -1).reshape(
        -1, ndim
    )
    rng = np.random.default_rng()
    rbins = rng.choice(grid, size=(nobj,), replace=False)

    # iterate over the bins and add a smaple
    centroids = []
    for v, bin in enumerate(rbins):
        sample, point = _sample()
        slices = tuple(
            [slice(b * binsize, b * binsize + binsize, 1) for b in bin]
        )
        val = 1 if binary else v + 1
        img[slices] = sample * val

        # shift the actual coordinates back to image space
        point = point + bin * binsize  # - 0.5
        centroids.append(point)

    # sort the centroids by axis
    centroids_arr = np.array(centroids)
    centroids_sorted = centroids[
        np.lexsort([centroids_arr[:, dim] for dim in range(ndim)][::-1])
    ]

    assert centroids_sorted.shape[0] == nobj
    return img, centroids


def _example_segmentation_generator():
    for i in range(10):
        img, centroids = _make_test_image()
        yield img


def _validate_centroids(centroids, objects, scale=None):
    """Take a list of objects and validate them agains the ground truth."""

    if centroids is None:
        assert not objects
        return

    if scale is not None:
        centroids = centroids * np.array(scale)

    obj_as_array = np.array([[obj.z, obj.y, obj.x] for obj in objects])
    if centroids.shape[-1] == 2:
        obj_as_array = obj_as_array[:, 1:]

    np.testing.assert_equal(obj_as_array, centroids)


def test_segmentation_to_objects_type():
    """Test that btrack objects are returned."""
    img, centroids = _make_test_image()
    objects = utils.segmentation_to_objects(img[np.newaxis, ...])
    assert all([isinstance(o, btypes.PyTrackObject) for o in objects])


def test_segmentation_to_objects_type_generator():
    """Test generator as input."""
    generator = _example_segmentation_generator()
    objects = utils.segmentation_to_objects(generator)
    assert all([isinstance(o, btypes.PyTrackObject) for o in objects])


@pytest.mark.parametrize("ndim", [2, 3])
@pytest.mark.parametrize("nobj", [0, 1, 10, 30, 300])
@pytest.mark.parametrize("binary", [True, False])
def test_segmentation_to_objects(ndim, nobj, binary):
    """Test different types of segmentation images."""
    img, centroids = _make_test_image(ndim=ndim, nobj=nobj, binary=True)
    objects = utils.segmentation_to_objects(img[np.newaxis, ...])
    _validate_centroids(centroids, objects)


@pytest.mark.parametrize("scale", [None, (1.0, 1.0), (1.0, 10.0), (10.0, 1.0)])
def test_segmentation_to_objects_scale(scale):
    """Test anisotropic scaling."""
    img, centroids = _make_test_image()
    objects = utils.segmentation_to_objects(img[np.newaxis, ...], scale=scale)
    _validate_centroids(centroids, objects, scale)
